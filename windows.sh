#!/bin/bash
#SBATCH --partition=high-mem
#SBATCH --time=01:00:00
#SBATCH --mem=100GB
#SBATCH -e outputs/ww_%j.err
#SBATCH -o outputs/ww_%j.out

start=$1
file=$2
end=$(expr $start + 1)
source $HOME/.conda/envs/ncdf/bin/activate
input_dir='/work/scratch-nopw/vicab/ww_per_location/'
# output_name='BCC-CSM1-1.nc'
# mkdir $input_dir

/usr/bin/env time -v python ncells_corr.py $start $file #&& python combine_locs.py $input_dir $start  

#rm $input_dir/*_"$start"-"$end"*.nc

# && makes sure that the second script only starts if the first script completed successfully
