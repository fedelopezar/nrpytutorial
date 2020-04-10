""" NRPy+ Loop Generation
    The following script generate a single or nested loop of arbitrary 
    dimension in C, and has support for cache blocking (loop tiling).
"""
# Author: Zachariah B. Etienne
    # Email: zachetie **at** gmail **dot* com
# Contributor: Ken Sible
    # Email: ksible **at** outlook **dot* com
import sys

def loop1D(idx_var='i', lower_bound='0', upper_bound='N', increment='1', pragma='#pragma omp parallel for', padding=''):
    """ Generate a one-dimensional loop in C.

            :arg:    index variable for the loop
            :arg:    lower bound on index variable
            :arg:    upper bound on index variable
            :arg:    increment for the index variable
            :arg:    OpenMP pragma (https://en.wikipedia.org/wiki/OpenMP)
            :arg:    padding before a line (tab number)
            :return: string header, string footer
            
            >>> header, footer = loop1D(pragma='')
            >>> print(header)
            for (int i = 0; i < N; i++) {
            <BLANKLINE>
            
            >>> print(footer)
            } // END LOOP: for (int i = 0; i < N; i++)
            <BLANKLINE>
            
            >>> header, footer = loop1D(increment='2', pragma='', padding='    ')
            >>> print(header)
                for (int i = 0; i < N; i += 2) {
            <BLANKLINE>
    """
    if any(not isinstance(i, str) for i in (idx_var, lower_bound, upper_bound, increment, pragma)):
        raise ValueError('all parameters must have type string.')
    pragma     = padding + pragma + '\n' if pragma else ''
    increment  = ' += ' + increment if increment != '1' else '++'
    header     = padding + 'for (int {i0} = {i1}; {i0} < {i2}; {i0}{i3})'.format(\
                     i0=idx_var, i1=lower_bound, i2=upper_bound, i3=increment)
    footer     = padding + '} // END LOOP: ' + header.strip() + '\n'
    return pragma + header + ' {\n', footer

def loop(idx_var, lower_bound, upper_bound, increment, pragma, padding='', interior="", tile_size=""):
    """ Generate a nested loop of arbitrary dimension in C.

            :arg:    index variable for the loop
            :arg:    lower bound on index variable
            :arg:    upper bound on index variable
            :arg:    increment for the index variable
            :arg:    OpenMP pragma (https://en.wikipedia.org/wiki/OpenMP)
            :arg:    padding before a line (tab number)
            :arg:    interior of the loop
            :arg:    tile size for cache blocking
            :return: (header, footer) or string of the loop
            
            >>> header, footer = loop('i', '0', 'N', '1', '')
            >>> print(header)
            for (int i = 0; i < N; i++) {
            <BLANKLINE>
            
            >>> print(footer)
            } // END LOOP: for (int i = 0; i < N; i++)
            <BLANKLINE>
            
            >>> print(loop('i', '0', 'N', '1', '', interior='print(i)'))
            for (int i = 0; i < N; i++) {
                print(i)
            } // END LOOP: for (int i = 0; i < N; i++)
            <BLANKLINE>
            
            >>> print(loop('i', '0', 'N', '1', '', interior='print(i)', tile_size='16'))
            for (int iB = 0; iB < N; iB += 16) {
                for (int i = iB; i < MIN(N, iB + 16); i++) {
                    print(i)
                } // END LOOP: for (int i = iB; i < MIN(N, iB + 16); i++)
            } // END LOOP: for (int iB = 0; iB < N; iB += 16)
            <BLANKLINE>
            
            >>> print(loop(['i', 'j'], ['0', '0'], ['Nx', 'Ny'], ['1', '1'], ['', ''], interior='print(i, j)'))
            for (int i = 0; i < Nx; i++) {
                for (int j = 0; j < Ny; j++) {
                    print(i, j)
                } // END LOOP: for (int j = 0; j < Ny; j++)
            } // END LOOP: for (int i = 0; i < Nx; i++)
            <BLANKLINE>
    """
    if (all(isinstance(i, str) for i in (idx_var, lower_bound, upper_bound, increment, pragma))):
        idx_var, lower_bound, upper_bound, increment, pragma = [idx_var], [lower_bound], [upper_bound], [increment], [pragma]
    length = len(idx_var)
    if any(len(i) != length for i in (lower_bound, upper_bound, increment, pragma)):
        raise ValueError('all list parameters must have the same length.')
    if tile_size:
        if isinstance(tile_size, str): tile_size = [tile_size]
        if len(tile_size) != length:
            raise ValueError('all list parameters must have the same length.')
    header_list, footer_list = [], []
    for i in range(length):
        if len(tile_size) > 0:
            ext_header, ext_footer = loop1D(idx_var[i] + 'B', lower_bound[i], upper_bound[i], tile_size[i], '', padding + i*'    ')
            header, footer = loop1D(idx_var[i], idx_var[i] + 'B', 'MIN(%s, %s + %s)' % (upper_bound[i], idx_var[i] + 'B', \
                tile_size[i]), increment[i], pragma[i], padding + (length + i)*'    ')
            header_list.insert(i, ext_header)
            footer_list.insert(i, ext_footer)
        else:
            header, footer = loop1D(idx_var[i], lower_bound[i], upper_bound[i], increment[i], pragma[i], padding + i*'    ')
        header_list.append(header)
        footer_list.append(footer)
    if interior:
        interior = [padding + (length + len(tile_size))*'    ' + line + '\n' for line in interior.split('\n')]
    header = ''.join(header_list)
    footer = ''.join(footer_list[::-1])
    if not interior: return header, footer
    return header + ''.join(interior) + footer

def simple_loop(options, interior):
    """ Generate a simple loop (for use inside a function) in C.

            :arg:    loop options
            :arg:    loop interior
            :return: string of the loop
            
            >>> print(simple_loop('AllPoints', ''))
                #pragma omp parallel for
                for (int i2 = 0; i2 < Nxx_plus_2NGHOSTS2; i2++) {
                    for (int i1 = 0; i1 < Nxx_plus_2NGHOSTS1; i1++) {
                        for (int i0 = 0; i0 < Nxx_plus_2NGHOSTS0; i0++) {
            <BLANKLINE>
            <BLANKLINE>
                        } // END LOOP: for (int i0 = 0; i0 < Nxx_plus_2NGHOSTS0; i0++)
                    } // END LOOP: for (int i1 = 0; i1 < Nxx_plus_2NGHOSTS1; i1++)
                } // END LOOP: for (int i2 = 0; i2 < Nxx_plus_2NGHOSTS2; i2++)
            <BLANKLINE>
    """
    if not options: return interior

    if "AllPoints" in options:
        i2i1i0_mins = ["0", "0", "0"]
        i2i1i0_maxs = ["Nxx_plus_2NGHOSTS2", "Nxx_plus_2NGHOSTS1", "Nxx_plus_2NGHOSTS0"]
        if "oldloops" in options:
            i2i1i0_maxs = ["Nxx_plus_2NGHOSTS[2]", "Nxx_plus_2NGHOSTS[1]", "Nxx_plus_2NGHOSTS[0]"]
    elif "InteriorPoints" in options:
        i2i1i0_mins = ["NGHOSTS","NGHOSTS","NGHOSTS"]
        i2i1i0_maxs = ["NGHOSTS+Nxx2","NGHOSTS+Nxx1","NGHOSTS+Nxx0"]
        if "oldloops" in options:
            i2i1i0_maxs = ["NGHOSTS+Nxx[2]", "NGHOSTS+Nxx[1]", "NGHOSTS+Nxx[0]"]
    else: raise ValueError('no interation space was specified.')

    Read_1Darrays = ["", "", ""]
    if "Read_xxs" in options:
        if not "EnableSIMD" in options:
            Read_1Darrays = ["const REAL xx0 = xx[0][i0];",
                             "            const REAL xx1 = xx[1][i1];",
                             "        const REAL xx2 = xx[2][i2];", ]
        else: raise ValueError('no SIMD support for Read_xxs (currently).')

    if "Enable_rfm_precompute" in options:
        if "Read_xxs" in options:
            raise ValueError('Enable_rfm_precompute and Read_xxs cannot both be enabled.')
        if "EnableSIMD" in options:
            Read_1Darrays = ["#include \"rfm_files/rfm_struct__SIMD_inner_read0.h\"",
                             "#include \"rfm_files/rfm_struct__SIMD_outer_read1.h\"",
                             "#include \"rfm_files/rfm_struct__SIMD_outer_read2.h\""]
        else:
            Read_1Darrays = ["#include \"rfm_files/rfm_struct__read0.h\"",
                             "#include \"rfm_files/rfm_struct__read1.h\"",
                             "#include \"rfm_files/rfm_struct__read2.h\""]

    pragma    = "" if "DisableOpenMP" in options else "#pragma omp parallel for"
    increment = ["1", "1", "SIMD_width"] if "EnableSIMD" in options else ["1","1","1"]
    tile_size = ["16", "16", "16"] if "EnableLoopTiling" in options else ""

    return loop(["i2","i1","i0"], i2i1i0_mins, i2i1i0_maxs, increment, [pragma, Read_1Darrays[2], Read_1Darrays[1]], \
        padding='    ', interior=Read_1Darrays[0] + "\n" + interior, tile_size=tile_size)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
