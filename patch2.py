import re
f = 'tools/write_tools.py'
c = open(f, encoding='utf-8').read()
c = c.replace('pattern = re.compile(Utente, re.IGNORECASE)', 'pattern = re.compile(f\'^{re.escape(Utente)}$\', re.IGNORECASE)')
c = c.replace('pattern = re.compile(nome_utente, re.IGNORECASE)', 'pattern = re.compile(f\'^{re.escape(nome_utente)}$\', re.IGNORECASE)')
c = c.replace('pattern = re.compile(f"^{nome}$", re.IGNORECASE)', 'pattern = re.compile(f\'^{re.escape(nome)}$\', re.IGNORECASE)')
open(f, 'w', encoding='utf-8').write(c)
f = 'tools/diario_tools.py'
c = open(f, encoding='utf-8').read()
c = c.replace('pattern = re.compile(nome_utente, re.IGNORECASE)', 'pattern = re.compile(f\'^{re.escape(nome_utente)}$\', re.IGNORECASE)')
open(f, 'w', encoding='utf-8').write(c)
print('Patched regexes')
