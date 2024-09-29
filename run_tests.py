from subprocess import getoutput, getstatusoutput
from os import listdir
from tqdm import tqdm

for test in tqdm(listdir('examples/correct')):
    output_file = test.replace(".hom", ".ok")
    comp_code, comp_out = getstatusoutput(f'bash run.sh examples/correct/{test}')
    if comp_code:
        print(f'Compilation of {test} failed\n{comp_out}')
        exit(1)

    exec_code, _ = getstatusoutput(f'./build/program.out > build/exec.stdout')
    getoutput(f'echo Return code is {exec_code} >> build/exec.stdout')

    if not output_file in listdir('examples/correct_outputs'):
        getoutput(f'cp build/exec.stdout examples/correct_outputs/{output_file}')

    diffout = getoutput(f'diff build/exec.stdout examples/correct_outputs/{output_file}')
    if diffout:
        print(f'Output of {test} changed')
        exit(1)

for test in tqdm(listdir('examples/incorrect')):
    comp_code, _ = getstatusoutput(f'bash run.sh examples/incorrect/{test}')
    if comp_code == 0:
        print(f'Compilatorion of {test} succeeded')
        exit(1)

print('OK')
