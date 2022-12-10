from srim import Ion, Layer, Target, TRIM
import os
import shutil
import time
import multiprocessing


Root_Folder = os.path.join('//media', 'sf_D_DRIVE')
Ion_Number = 10000
min_Energy = 400000
max_Energy = 2900000
Energy_steps = 2500000


def simulate_transmission(energy_index, ion_energy):
    width = ion_energy/40
    data_folder = os.path.join(Root_Folder, 'SRIM_DATA', 'Transmit_{:0.0f}keV'.format(ion_energy / 1000))
    program_folder = os.path.join(Root_Folder, 'Programme', 'SRIM', 'SRIM - Copy ({})'.format(energy_index+1))
    if os.path.join('Transmit_{:0.0f}keV'.format(ion_energy / 1000)) in os.listdir(os.path.join(Root_Folder, 'SRIM_DATA')):
        shutil.rmtree(data_folder)
    os.mkdir(data_folder)
    ion = Ion('Si', energy=ion_energy)
    start_time = time.time()

    steel_layer = Layer.from_formula('C100', density=3.51, width=width,
                                     E_disp={'C': 43.3},
                                     E_lattice={'C': 27.7},
                                     E_surface={'C': 27.7}, name='Diamond')
    target = Target([steel_layer])
    trim = TRIM(target, ion, number_ions=Ion_Number, calculation=1, transmit=False,
                collisions=True, backscattered=False, sputtered=False, ranges=True)
    trim.run(program_folder)
    shutil.move(os.path.join(program_folder, 'SRIM Outputs', 'COLLISON.txt'),
                os.path.join(data_folder, 'COll_{}.txt'.format(str(width).zfill(4))))
    shutil.move(os.path.join(program_folder, 'SRIM Outputs', 'RANGE_3D.txt'),
                os.path.join(data_folder, 'RANG_{}.txt'.format(str(width).zfill(4))))

    print('Calculated transmission for {}keV through {}nm layer'.format(ion_energy/1000, width / 10),
          'in {:1.3f} sec'.format(time.time() - start_time))
    print('Total elapsed time is: {} seconds'.format(time.time() - start_time))


energy_list = [[index, energy] for index, energy in
               enumerate(range(min_Energy, max_Energy + Energy_steps, Energy_steps))]
for index in range(len(energy_list)):
    if index % 8 == 4:
        energy_list[index:index+4] = reversed(energy_list[index:index+4])

pool = multiprocessing.Pool(processes=4)
pool.starmap_async(simulate_transmission, energy_list)
pool.close()
pool.join()
