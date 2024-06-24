#!/bin/bash
#
#SBATCH --job-name=05-AlCo2S4
#
##### STDOUT/STDERR OUTPUT OF JOB:
#
# # %x will be replaced by job name, %j by job id
#
#SBATCH --output=%x.%j
#SBATCH --error=%x.%j
#
##### E-MAIL SPECIFICATION:
#
# # No emails are send by default. Replace LINUX_USER_NAME with your user name.
#
#SBATCH --mail-type=END
#SBATCH --mail-user=mohsen.sotoudeh@uni-ulm.de
#
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=48
#
#SBATCH --mem-per-cpu=3500M
#       --gres=scratch:800
#
#SBATCH --time=24:00:00
#
# # For possible node-local disk sizes see node properties of the cluster:
# #     https://wiki.bwhpc.de/e/Main_Page => JUSTUS 2 => Hardware/Queues
#
########## END QUEUEING SYSTEM JOB PARAMETERS.



echo " "
echo "### Setting up shell environment and defaults for environment vars ..."
echo " "
# Reset all language and locale dependencies (write floats with a dot "."):
unset LANG; export LC_ALL="C"
# Disable all external multi-threading => MPI is in control
export MKL_NUM_THREADS=1; export OMP_NUM_THREADS=1
# Define fallbacks and "sanitize" important environment variables:
export USER="${USER:=`logname`}"
export SLURM_JOB_ID="${SLURM_JOB_ID:=`date +%s`}"
export SLURM_SUBMIT_DIR="${SLURM_SUBMIT_DIR:=`pwd`}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME:=`basename "$0"`}"
export SLURM_JOB_NAME="${SLURM_JOB_NAME//[^a-zA-Z0-9._-]/_}"
export SLURM_JOB_NUM_NODES="${SLURM_JOB_NUM_NODES:=1}"
export SLURM_CPUS_ON_NODE="${SLURM_CPUS_ON_NODE:=1}"
export SLURM_NTASKS="${SLURM_NTASKS:=1}"
# Increase stack limit to 200M per MPI process (10M system default not sufficient):
ulimit -s 200000



echo " "
echo "### Printing basic job infos to stdout ..."
echo " "
echo "START_TIME             = `date +'%y-%m-%d %H:%M:%S %s'`"
echo "HOSTNAME               = ${HOSTNAME}"
echo "USER                   = ${USER}"
echo "SLURM_JOB_NAME         = ${SLURM_JOB_NAME}"
echo "SLURM_JOB_ID           = ${SLURM_JOB_ID}"
echo "SLURM_SUBMIT_DIR       = ${SLURM_SUBMIT_DIR}"
echo "SLURM_JOB_NUM_NODES    = ${SLURM_JOB_NUM_NODES}"
echo "SLURM_CPUS_ON_NODE     = ${SLURM_CPUS_ON_NODE}"
echo "SLURM_NTASKS           = ${SLURM_NTASKS}"
echo "SLURM_JOB_NODELIST     = ${SLURM_JOB_NODELIST}"
echo "---------------- ulimit -a -S ----------------"
ulimit -a -S
echo "---------------- ulimit -a -H ----------------"
ulimit -a -H
echo "----------------------------------------------"



echo " "
echo "### Creating TMP_WORK_DIR directory and changing to it ..."
echo " "
# Single-node jobs => use "${SCRATCH}" as base
# Multi-node jobs  => use "$SLURM_SUBMIT_DIR" (assuming that job has been
#                     submitted from within a workspace area)
# NEVER EVER calculate in your home directory.
TMP_BASE_DIR="$SLURM_SUBMIT_DIR"
JOB_WORK_DIR="${SLURM_JOB_NAME}.${SLURM_JOB_ID%%.*}.$(date +%y%m%d_%H%M%S)"
TMP_WORK_DIR="${TMP_BASE_DIR}/${JOB_WORK_DIR}"
echo "TMP_BASE_DIR           = ${TMP_BASE_DIR}"
echo "JOB_WORK_DIR           = ${JOB_WORK_DIR}"
echo "TMP_WORK_DIR           = ${TMP_WORK_DIR}"
mkdir -vp "${TMP_WORK_DIR}"
cd "${TMP_WORK_DIR}"
#cp -v "$0" "${TMP_WORK_DIR}/"



echo " "
echo "### Loading software module:"
echo " "
#module unload chem/vasp
#module load chem/vasp/5.4.4.3.16052018
module load compiler/intel
module load mpi/impi
module load numlib/mkl
module load chem/vasp/5.4.4.3.16052018
module list

echo " "
echo "### Copying input files to TMP_WORK_DIR:"
echo " "
cp ${SLURM_SUBMIT_DIR}/INCAR   ./INCAR
cp ${SLURM_SUBMIT_DIR}/KPOINTS ./KPOINTS
cp ${SLURM_SUBMIT_DIR}/POSCAR  ./POSCAR
cp ${SLURM_SUBMIT_DIR}/POTCAR  ./POTCAR

echo " "
echo "### Running application ..."
echo " "

# Put the VASP binary in your home directory
# Do not forget to change the file attribute for executable: chmod 755 vasp_std
time vasp
exit_code=$?
echo ""
echo "VASP finished with exit code $exit_code"

echo " "
echo "### Cleaning up files ... removing unnecessary scratch files ..."
echo " "
#rm -vf CHG CHG.* EIGENVAL* IBZKPT* PCDAT* PROCAR* XDATCAR* vasprun.xml \
#       CONTCAR DOSCAR* ELFCAR* LOCPOT* OUTPAR* PROOUT* \
#       CHGCAR* TMPCAR* WAVECAR* POTCAR vasp.dipcor
sleep 10 # Sleep some time so potential stale nfs handles can disappear
# Remarks:
# * PLEASE remove all not required files in this script.



echo " "
echo "### Copying back tgz-archive of results to SLURM_SUBMIT_DIR ..."
echo " "
mkdir -vp "${SLURM_SUBMIT_DIR}" # if submit dir has been deleted or moved away
echo "Creating result tgz-file '${SLURM_SUBMIT_DIR}/${JOB_WORK_DIR}.tgz' ..."
cd "${TMP_BASE_DIR}"
tar -zcvf "${JOB_WORK_DIR}.tgz" "${JOB_WORK_DIR}" \
  || { echo "ERROR: Failed to create tgz-file. Please cleanup TMP_WORK_DIR '$TMP_WORK_DIR' on host '$HOSTNAME' manually (if not done automatically by queueing system)."; exit 102; }
# Remarks:
# * Please include only those result files that are really required
#   for further steps. Everything else is a waste of disk space.

cp -rv  $TMP_WORK_DIR/CONTCAR $SLURM_SUBMIT_DIR
cp -rv  $TMP_WORK_DIR/OSZICAR $SLURM_SUBMIT_DIR
cp -rv  $TMP_WORK_DIR/OUTCAR $SLURM_SUBMIT_DIR

echo " "
echo "### Final cleanup: Remove TMP_WORK_DIR ..."
echo " "
cd "${TMP_BASE_DIR}"
rm -rvf "${TMP_WORK_DIR}"
rm -rvf "${TMP_WORK_DIR}.tgz"
echo "END_TIME               = `date +'%y-%m-%d %H:%M:%S %s'`"



echo " "
echo "### Exiting with exit code '$exit_code' ..."
echo " "
exit $exit_code
