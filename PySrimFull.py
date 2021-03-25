from srim import Ion, Layer, Target, TRIM
import os
import shutil
import time
import multiprocessing

Root_Folder = os.path.join('//media', 'sf_D_DRIVE')
Ion_Number = 10000
processes = 4
min_Energy = 400000
max_Energy = 400000
Energy_steps = 1000000
nFiles = 40


def find_optimum_steps(ion, program_folder):
    initial_steps = 100000
    file_number = 0
    while file_number < nFiles * 0.2:
        for test_width_index, test_width in enumerate(range(int(initial_steps), 10000000, int(initial_steps))):
            test_layer = Layer.from_formula('Cr8Fe74Ni18', density=8, width=test_width,
                                            E_disp={'Cr': 25, 'Fe': 25, 'Ni': 25},
                                            E_lattice={'Cr': 3, 'Fe': 3, 'Ni': 3},
                                            E_surface={'Cr': 4.12, 'Fe': 4.34, 'Ni': 4.46}, name='StainlessSteel')
            test_target = Target([test_layer])
            test_trim = TRIM(test_target, ion, number_ions=10, calculation=1, transmit=True,
                             collisions=False, backscattered=False, sputtered=False, ranges=False)
            test_trim.run(program_folder)
            with open(os.path.join(program_folder, 'SRIM Outputs', 'TRANSMIT.txt'), 'r+') as test_output_file:
                test_data = test_output_file.read().splitlines()[12:]
            if len(test_data) < 5:
                file_number = (test_width_index + 1)
                initial_steps *= file_number / nFiles
                break
    return initial_steps


def simulate_transmission(energy_index, ion_energy):
    data_folder = os.path.join(Root_Folder, 'SRIM_DATA', 'Transmit_{:0.0f}keV'.format(ion_energy / 1000))
    program_folder = os.path.join(Root_Folder, 'Programme', 'SRIM', 'SRIM - Copy ({})'.format(energy_index + 1))
    os.mkdir(data_folder)
    ion = Ion('Si', energy=ion_energy)
    width_steps = find_optimum_steps(ion, program_folder)
    for width_index, width in enumerate(range(int(width_steps) + 1, 10 ** 7, int(width_steps) + 1)):
        start_time = time.time()
        steel_layer = Layer.from_formula('Cr8Fe74Ni18', density=8, width=width,
                                         E_disp={'Cr': 25, 'Fe': 25, 'Ni': 25},
                                         E_lattice={'Cr': 3, 'Fe': 3, 'Ni': 3},
                                         E_surface={'Cr': 4.12, 'Fe': 4.34, 'Ni': 4.46}, name='StainlessSteel')
        prop_layer = Layer.from_formula('H1', density=10 ** -10, width=10 ** 7,
                                        E_disp={'H': 0}, E_lattice={'H': 0}, E_surface={'H': 0}, name='Propagation')
        target = Target([steel_layer, prop_layer])
        trim = TRIM(target, ion, number_ions=Ion_Number, calculation=1, transmit=True,
                    collisions=False, backscattered=False, sputtered=False, ranges=False)
        trim.run(program_folder)
        shutil.move(os.path.join(program_folder, 'SRIM Outputs', 'TRANSMIT.txt'),
                    os.path.join(data_folder, 'TRANSMIT.txt'))
        with open(os.path.join(data_folder, 'TRANSMIT.txt'), 'r+') as output_file:
            data = output_file.read().splitlines()[12:]
        with open(os.path.join(data_folder, '{}.txt'.format(str(width).zfill(4))), 'w+') as transmit_data:
            for line in data:
                transmit_data.write(line + '\n')
        print('Calculated transmission for {}keV through {}nm layer'.format(ion_energy/1000, width / 10),
              'in {:1.3f} sec'.format(time.time() - start_time))
        if width_index + 1 == nFiles:
            os.remove(os.path.join(data_folder, 'TRANSMIT.txt'))
            break


start_time = time.time()
energy_list = [[index, energy] for index, energy in
               enumerate(range(min_Energy, max_Energy + Energy_steps, Energy_steps))]
for index in range(len(energy_list)):
    if index % 8 == 4:
        energy_list[index:index+4] = reversed(energy_list[index:index+4])

pool = multiprocessing.Pool(processes=processes)
pool.starmap_async(simulate_transmission, energy_list)
pool.close()
pool.join()
print('Total elapsed time is: {} seconds'.format(time.time() - start_time))
