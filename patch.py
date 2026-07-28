import re
for f in ['tools/diario_tools.py', 'tools/read_tools.py', 'tools/write_tools.py']:
    c = open(f, encoding='utf-8').read()
    c = re.sub(r'get_collection\((f?".*?")\)', r'get_collection(\1, uid)', c)
    open(f, 'w', encoding='utf-8').write(c)
print('Done!')
