
# Step 1: Import needed core NRPy+ modules
import NRPy_param_funcs as par # NRPy+: Parameter interface
import grid as gri             # NRPy+: Functions having to do with numerical grids
import os, sys                 # Standard Python modules for multiplatform OS-level functions

def keep_param__return_type(paramtuple):
    keep_param = True # We'll not set some parameters in param.ccl;
                      #   e.g., those that should be #define'd like M_PI.
    typestring = ""
    # Separate thorns within the ETK take care of grid/coordinate parameters;
    #   thus we ignore NRPy+ grid/coordinate parameters:
    if paramtuple.module == "grid" or paramtuple.module == "reference_metric":
        keep_param = False

    partype = paramtuple.type
    if partype == "bool":
        typestring += "BOOLEAN "
    elif partype == "REAL":
        if paramtuple.defaultval != 1e300: # 1e300 is a magic value indicating that the C parameter should be mutable
            typestring += "CCTK_REAL "
        else:
            keep_param = False
    elif partype == "int":
        typestring += "CCTK_INT "
    elif partype == "#define":
        keep_param = False
    elif partype == "char":
        # FIXME: char/string parameter types should in principle be supported
        print("Error: parameter "+paramtuple.module+"::"+paramtuple.parname+
              " has unsupported type: \""+ paramtuple.type + "\"")
        sys.exit(1)
    else:
        print("Error: parameter "+paramtuple.module+"::"+paramtuple.parname+
              " has unsupported type: \""+ paramtuple.type + "\"")
        sys.exit(1)
    return keep_param, typestring

def output_param_ccl(ThornName="BaikalETK"):
    with open(os.path.join(ThornName,"param.ccl"), "w") as file:
        file.write("""
# This param.ccl file was automatically generated by NRPy+.
#   You are advised against modifying it directly; instead
#   modify the Python code that generates it.

shares: ADMBase   # Extends multiple ADMBase variables:

EXTENDS CCTK_KEYWORD evolution_method "evolution_method"
{
  "BaikalETK" :: ""
}

EXTENDS CCTK_KEYWORD lapse_evolution_method "lapse_evolution_method"
{
  "BaikalETK" :: ""
}

EXTENDS CCTK_KEYWORD shift_evolution_method "shift_evolution_method"
{
  "BaikalETK" :: ""
}

EXTENDS CCTK_KEYWORD dtshift_evolution_method "dtshift_evolution_method"
{
  "BaikalETK" :: ""
}

EXTENDS CCTK_KEYWORD dtlapse_evolution_method "dtlapse_evolution_method"
{
  "BaikalETK" :: ""
}

restricted:

CCTK_INT FD_order "Finite-differencing order"
{\n""".replace("BaikalETK",ThornName))
        FDorders = []
        for _root, _dirs, files in os.walk(os.path.join(ThornName,"src")): # _root,_dirs unused.
            for Cfilename in files:
                if ("BSSN_Ricci_FD_order" in Cfilename) and (".h" in Cfilename):
                    array = Cfilename.replace(".","_").split("_")
                    FDorders.append(int(array[-2]))
        FDorders.sort()
        for order in FDorders:
            file.write(" "+str(order)+":"+str(order)+"   :: \"finite-differencing order = "+str(order)+"\"\n")
        FDorder_default = 4
        if FDorder_default not in FDorders:
            print("WARNING: 4th-order FD kernel was not output!?! Changing default FD order to "+str(FDorders[0]))
            FDorder_default = FDorders[0]
        file.write("} "+str(FDorder_default)+ "\n\n") # choose 4th order by default, consistent with ML_BSSN
        paramccl_str = ""
        for i in range(len(par.glb_Cparams_list)):
            # keep_param is a boolean indicating whether we should accept or reject
            #    the parameter. singleparstring will contain the string indicating
            #    the variable type.
            keep_param, singleparstring = keep_param__return_type(par.glb_Cparams_list[i])

            if keep_param:
                parname = par.glb_Cparams_list[i].parname
                partype = par.glb_Cparams_list[i].type
                singleparstring += parname + " \""+ parname +" (see NRPy+ for parameter definition)\"\n"
                singleparstring += "{\n"
                if partype != "bool":
                    singleparstring += " *:* :: \"All values accepted. NRPy+ does not restrict the allowed ranges of parameters yet.\"\n"
                singleparstring += "} "+str(par.glb_Cparams_list[i].defaultval)+"\n\n"

                paramccl_str += singleparstring
        file.write(paramccl_str)

# First construct lists of the basic gridfunctions used in NRPy+.
#    Each type will be its own group in BaikalETK.
evol_gfs_list    = []
auxevol_gfs_list = []
aux_gfs_list     = []
for i in range(len(gri.glb_gridfcs_list)):
    if gri.glb_gridfcs_list[i].gftype == "EVOL":
        evol_gfs_list.append(   gri.glb_gridfcs_list[i].name+"GF")

    if gri.glb_gridfcs_list[i].gftype == "AUX":
        aux_gfs_list.append(    gri.glb_gridfcs_list[i].name+"GF")

    if gri.glb_gridfcs_list[i].gftype == "AUXEVOL":
        auxevol_gfs_list.append(gri.glb_gridfcs_list[i].name+"GF")

# NRPy+'s finite-difference code generator assumes gridfunctions
#    are alphabetized; not sorting may result in unnecessary
#    cache misses.
evol_gfs_list.sort()
aux_gfs_list.sort()
auxevol_gfs_list.sort()
rhs_list = []
for gf in evol_gfs_list:
    rhs_list.append(gf.replace("GF","")+"_rhsGF")

def output_interface_ccl(ThornName="BaikalETK",enable_stress_energy_source_terms=False):
    outstr = """
# This interface.ccl file was automatically generated by NRPy+.
#   You are advised against modifying it directly; instead
#   modify the Python code that generates it.

# With "implements", we give our thorn its unique name.
implements: BaikalETK

# By "inheriting" other thorns, we tell the Toolkit that we
#   will rely on variables/function that exist within those
#   functions.
inherits:   ADMBase Boundary Grid MethodofLines\n"""
    if enable_stress_energy_source_terms == True:
        outstr += "inherits:   TmunuBase\n"
    outstr += """
# Needed functions and #include's:
USES INCLUDE: Symmetry.h
USES INCLUDE: Boundary.h

# Needed Method of Lines function
CCTK_INT FUNCTION MoLRegisterEvolvedGroup(CCTK_INT IN EvolvedIndex, \
                                          CCTK_INT IN RHSIndex)
REQUIRES FUNCTION MoLRegisterEvolvedGroup

# Needed Boundary Conditions function
CCTK_INT FUNCTION GetBoundarySpecification(CCTK_INT IN size, CCTK_INT OUT ARRAY nboundaryzones, CCTK_INT OUT ARRAY is_internal, CCTK_INT OUT ARRAY is_staggered, CCTK_INT OUT ARRAY shiftout)
USES FUNCTION GetBoundarySpecification

CCTK_INT FUNCTION SymmetryTableHandleForGrid(CCTK_POINTER_TO_CONST IN cctkGH)
USES FUNCTION SymmetryTableHandleForGrid

CCTK_INT FUNCTION Boundary_SelectVarForBC(CCTK_POINTER_TO_CONST IN GH, CCTK_INT IN faces, CCTK_INT IN boundary_width, CCTK_INT IN table_handle, CCTK_STRING IN var_name, CCTK_STRING IN bc_name)
USES FUNCTION Boundary_SelectVarForBC

# Needed to determine boundary sizes for applying boundary conditions to BSSN constraint gridfunctions
CCTK_INT FUNCTION GetBoundarySizesAndTypes \
  (CCTK_POINTER_TO_CONST IN cctkGH, \
   CCTK_INT IN size, \
   CCTK_INT OUT ARRAY bndsize, \
   CCTK_INT OUT ARRAY is_ghostbnd, \
   CCTK_INT OUT ARRAY is_symbnd, \
   CCTK_INT OUT ARRAY is_physbnd)
REQUIRES FUNCTION GetBoundarySizesAndTypes

# Needed for EinsteinEvolve/NewRad outer boundary condition driver:
CCTK_INT FUNCTION                         \\
    NewRad_Apply                          \\
        (CCTK_POINTER_TO_CONST IN cctkGH, \\
         CCTK_REAL ARRAY IN var,          \\
         CCTK_REAL ARRAY INOUT rhs,       \\
         CCTK_REAL IN var0,               \\
         CCTK_REAL IN v0,                 \\
         CCTK_INT IN radpower)
REQUIRES FUNCTION NewRad_Apply

# Needed to convert ADM initial data into BSSN initial data (gamma extrapolation)
CCTK_INT FUNCTION                         \\
    ExtrapolateGammas                     \\
        (CCTK_POINTER_TO_CONST IN cctkGH, \\
         CCTK_REAL ARRAY INOUT var)
REQUIRES FUNCTION ExtrapolateGammas

# Tell the Toolkit that we want all gridfunctions
#    to be visible to other thorns by using
#    the keyword "public". Note that declaring these
#    gridfunctions *does not* allocate memory for them;
#    that is done by the schedule.ccl file.

# FIXME: add info for symmetry conditions:
#    https://einsteintoolkit.org/thornguide/CactusBase/SymBase/documentation.html
public:
"""

    # Next we declare gridfunctions based on their corresponding gridfunction groups as registered within NRPy+

    def output_list_of_gfs(gfs_list,description="User did not provide description"):
        gfs_list_parsed = []
        for i in range(len(gfs_list)):
            # Do not add T4UU gridfunctions if enable_stress_energy_source_terms==False:
            if not (enable_stress_energy_source_terms==False and "T4UU" in gfs_list[i]):
                gfs_list_parsed.append(gfs_list[i])
        gfsstr = "    "
        for i in range(len(gfs_list_parsed)):
            gfsstr += gfs_list_parsed[i]
            if i != len(gfs_list_parsed)-1:
                gfsstr += "," # This is a comma-separated list of gridfunctions
            else:
                gfsstr += "\n} \""+description+"\"\n\n"
        return gfsstr
    # First EVOL type:
    outstr += "CCTK_REAL evol_variables type = GF Timelevels=3\n{\n"
    outstr += output_list_of_gfs(evol_gfs_list,"BSSN evolved gridfunctions")
    # Second EVOL right-hand-sides
    outstr += "CCTK_REAL evol_variables_rhs type = GF Timelevels=1 TAGS=\'InterpNumTimelevels=1 prolongation=\"none\"\'\n{\n"
    outstr += output_list_of_gfs(rhs_list,"right-hand-side storage for BSSN evolved gridfunctions")
    # Then AUX type:
    outstr += "CCTK_REAL aux_variables type = GF Timelevels=3\n{\n"
    outstr += output_list_of_gfs(aux_gfs_list,"Auxiliary gridfunctions for BSSN diagnostics")
    # Finally, AUXEVOL type:
    outstr += "CCTK_REAL auxevol_variables type = GF Timelevels=1 TAGS=\'InterpNumTimelevels=1 prolongation=\"none\"\'\n{\n"
    outstr += output_list_of_gfs(auxevol_gfs_list,"Auxiliary gridfunctions needed for evaluating the BSSN RHSs")

    with open(os.path.join(ThornName,"interface.ccl"), "w") as file:
        file.write(outstr.replace("BaikalETK",ThornName))

def output_schedule_ccl(ThornName="BaikalETK",enable_stress_energy_source_terms=False):
    outstr = """
# This schedule.ccl file was automatically generated by NRPy+.
#   You are advised against modifying it directly; instead
#   modify the Python code that generates it.

# First allocate storage for one timelevel of ADMBase gridfunctions, which is the
#    bare minimum needed by NRPy+. If another thorn (e.g., ADMBase itself) requests
#    more timelevels of storage, Cactus automatically allocates the maximum requested.
STORAGE: ADMBase::metric[1], ADMBase::curv[1], ADMBase::lapse[1], ADMBase::shift[1]

# Next allocate storage for all 3 gridfunction groups used in BaikalETK
STORAGE: evol_variables[3]     # Evolution variables
STORAGE: evol_variables_rhs[1] # Variables storing right-hand-sides
STORAGE: aux_variables[3]      # Diagnostics variables
STORAGE: auxevol_variables[1]  # Single-timelevel storage of variables needed for evolutions.

# The following scheduler is based on Lean/LeanBSSNMoL/schedule.ccl

schedule BaikalETK_Banner at STARTUP
{
  LANG: C
  OPTIONS: meta
} "Output ASCII art banner"

schedule BaikalETK_RegisterSlicing at STARTUP after BaikalETK_Banner
{
  LANG: C
  OPTIONS: meta
} "Register 3+1 slicing condition"

schedule BaikalETK_Symmetry_registration at BASEGRID
{
  LANG: C
  OPTIONS: Global
} "Register symmetries, the CartGrid3D way."

schedule BaikalETK_zero_rhss at BASEGRID after BaikalETK_Symmetry_registration
{
  LANG: C
} "Idea from Lean: set all rhs functions to zero to prevent spurious nans"

schedule BaikalETK_ADM_to_BSSN at CCTK_INITIAL after ADMBase_PostInitial
{
  LANG: C
  OPTIONS: Local
  SYNC: evol_variables
} "Convert initial data into BSSN variables"

schedule GROUP ApplyBCs as BaikalETK_ApplyBCs at CCTK_INITIAL after BaikalETK_ADM_to_BSSN
{
} "Apply boundary conditions"


# MoL: registration

schedule BaikalETK_MoL_registration in MoL_Register
{
  LANG: C
  OPTIONS: META
} "Register variables for MoL"


# MoL: compute RHSs, etc
"""
    if enable_stress_energy_source_terms == True:
        outstr += """
schedule BaikalETK_driver_BSSN_T4UU in MoL_CalcRHS as BaikalETK_T4UU before BaikalETK_BSSN_to_ADM
{
  LANG: C
} "MoL: Compute T4UU, needed for BSSN RHSs."
"""
    outstr += """
schedule BaikalETK_driver_pt1_BSSN_Ricci in MoL_CalcRHS as BaikalETK_Ricci before BaikalETK_RHS
{
  LANG: C
} "MoL: Compute Ricci tensor"

schedule BaikalETK_driver_pt2_BSSN_RHSs in MoL_CalcRHS as BaikalETK_RHS after BaikalETK_Ricci
{
  LANG: C
} "MoL: Evaluate BSSN RHSs"

schedule BaikalETK_NewRad in MoL_CalcRHS after BaikalETK_RHS
{
  LANG: C
} "NewRad boundary conditions, scheduled right after RHS eval."

schedule BaikalETK_floor_the_lapse in MoL_PostStep before BaikalETK_enforce_detgammabar_constraint before BC_Update
{
  LANG: C
} "Set lapse = max(lapse_floor, lapse)"

schedule BaikalETK_enforce_detgammabar_constraint in MoL_PostStep before BC_Update
{
  LANG: C
} "Enforce detgammabar = detgammahat (= 1 in Cartesian)"

schedule BaikalETK_BoundaryConditions_evolved_gfs in MoL_PostStep
{
  LANG: C
  OPTIONS: LEVEL
  SYNC: evol_variables
} "Apply boundary conditions and perform AMR+interprocessor synchronization"

schedule GROUP ApplyBCs as BaikalETK_ApplyBCs in MoL_PostStep after BaikalETK_BoundaryConditions_evolved_gfs
{
} "Group for applying boundary conditions"


# Next update ADM quantities

schedule BaikalETK_BSSN_to_ADM in MoL_PostStep after BaikalETK_ApplyBCs before ADMBase_SetADMVars
{
  LANG: C
  OPTIONS: Local
} "Perform BSSN-to-ADM conversion. Useful for diagnostics."

# Compute Hamiltonian & momentum constraints
"""
    if enable_stress_energy_source_terms == True:
        outstr += """
schedule BaikalETK_driver_BSSN_T4UU in MoL_PseudoEvolution before BaikalETK_BSSN_constraints
{
  LANG: C
  OPTIONS: Local
} "MoL_PseudoEvolution: Compute T4UU, needed for BSSN constraints"
"""
    outstr += """

schedule BaikalETK_BSSN_constraints in MoL_PseudoEvolution
{
  LANG: C
  OPTIONS: Local
} "Compute BSSN (Hamiltonian and momentum) constraints"

schedule BaikalETK_BoundaryConditions_aux_gfs in MoL_PseudoEvolution after BaikalETK_BSSN_constraints
{
  LANG: C
  OPTIONS: LEVEL
  SYNC: aux_variables
} "Enforce symmetry BCs in constraint computation"

"""
    if enable_stress_energy_source_terms == True:
        outstr += """
schedule BaikalETK_BSSN_to_ADM in MoL_PseudoEvolution after BaikalETK_BoundaryConditions_aux_gfs
{
  LANG: C
  OPTIONS: Local
} "Perform BSSN-to-ADM conversion in MoL_PseudoEvolution. Needed for proper HydroBase integration."
"""
    outstr += """
schedule GROUP ApplyBCs as BaikalETK_auxgfs_ApplyBCs in MoL_PseudoEvolution after BaikalETK_BoundaryConditions_aux_gfs
{
} "Apply boundary conditions"
"""
    with open(os.path.join(ThornName,"schedule.ccl"), "w") as file:
        file.write(outstr.replace("BaikalETK",ThornName))
