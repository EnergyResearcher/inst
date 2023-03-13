import xarray as xr
import pandas as pd
import argparse

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('start')
    parser.add_argument('file')
    return parser.parse_args()

def prep_global(path, start):
    ds = xr.open_dataset(path)
    ds = ds.sel(time=slice(str(start),str(start+1)))
    #ds = ds.where(ds.lat >= 0, drop=True)
    #ds = ds.dropna(dim='ncells',how='all')
    ds['bool'] = xr.where(ds.hs <= 1.5, 1, 0).astype('int16') # set the threshold as a variable
    ds['id'] = (ds.bool.diff('time').fillna(0) != 0).cumsum('time').astype('int16')
    #stacked = ds.stack(location=('lat','lon')) # already stacked
    return ds
    
def pivot(stacked, i):
    df = stacked.isel(ncells=i).to_dataframe().reset_index()
    windows = df.groupby(['bool','id']).bool.size() #this loses 'time' coordinate
    
    # continue to split rows with False/True into weather windows and waiting periods
    # note the time step in the original data - this will impact what each counted period mean, e.g. 3 hours or 6 hours
    # save the values
    
    starts = df.groupby(['bool','id']).time.first()
    combined = pd.concat([windows,starts],axis=1)
    combined.columns = ['duration', 'time']
    return combined

def rearrange_pivot(combined, i):
    combined = combined.reset_index()
    combined = combined.rename(columns={'bool':'period_type'}) # here 1 is weather window, 0 is waiting period
    #combined['period_type'] = combined.above.map({True:'waiting', False:'working'}) # check which one is which based on "greater than"/"less than" criteria
    #combined.drop(columns=['id'], inplace=True)
    
    ncells = pd.Series([i] * len(combined))
    mdx = pd.MultiIndex.from_arrays([ncells, combined.time], names=['ncells','time'])
    combined.set_index(mdx, inplace=True)
    combined.drop(columns=['id','time'], inplace=True)
    return combined

def main():
    start = int(parser().start)
    file = parser().file
    model = file[:-13]
    path = f"/work/scratch-nopw/vicab/cowclip/eccc_d/{file}.nc"
    #path = '/home/users/vicab/transfer/BCC_1979-1988_test.nc'
    print(path)
    dataset = prep_global(path, start)
    # convert longitudes from 0-359 to -180-179
    dataset = dataset.assign_coords(lon=(((dataset.lon + 180) % 360) - 180))
    locs = dataset['ncells'].values

    single_ds = []
    for i in locs[:15000]: 
        print(f'[INFO] Starting processing location {i+1} of {len(locs[:15000])}')
        loc = float(dataset.isel(ncells=i).lon), float(dataset.isel(ncells=i).lat)
        ds = pivot(dataset, i)
        ds = rearrange_pivot(ds, i)
        
        #mindexed.drop(columns=['time'], inplace=True)
        #single_ds.append(mindexed.to_xarray())
        ds = ds.to_xarray()
        ds = ds.assign_coords({'lon':('ncells', [loc[0]]), 'lat':('ncells',[loc[1]])})
        ds['lon'] = ds['lon'].astype('int16')
        ds['lat'] = ds['lat'].astype('int16')
        ds['period_type'] = xr.where(ds['period_type'] == 1, True, False)
        
        single_ds.append(xr.where((ds.duration >= 3) & (ds.period_type == True), True, False).rename('mask_3h'))
        #ds_x.to_netcdf(f'/work/scratch-nopw/vicab/ww_per_location/{model}_{start}-{start+1}_{i}.nc')

    dataset = xr.merge(single_ds)
    print(dataset)
    
    #print(mask)
    dataset.attrs = {'description': 'The mask is True for points where weather windows is longer than 3 hours'}
    dataset.to_netcdf(f'/work/scratch-nopw/vicab/3hmask/{model}_{start}-{start+1}_{i}.nc')

if __name__=='__main__':
    main()