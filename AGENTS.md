fix the bug that is causing this:

Alen@bazzite:~/Desktop/SolarEx$ python solarx.py
[SolarEx] Booting modular web system…
[SolarEx] Using profile: <Profile Default incognito=False>
[SolarEx] Loaded module 'net' from 'solarex.net'
/usr/lib/python3.14/site-packages/anyio/from_thread.py:119: SyntaxWarning: 'return' in a 'finally' block
  return result
[SolarEx] Module 'net' already registered, replacing.
[SolarEx] Loaded module 'net' from 'solarex.net.httpx_backend'
Traceback (most recent call last):
  File "/var/home/Alen/Desktop/SolarEx/solarx.py", line 70, in <module>
    main()
    ~~~~^^
  File "/var/home/Alen/Desktop/SolarEx/solarx.py", line 35, in main
    core.load("solarex.render.manager", as_name="render")
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/home/Alen/Desktop/SolarEx/solarex/core/modules.py", line 31, in load
    mod = import_module(dotted)
  File "/usr/lib64/python3.14/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 758, in exec_module
  File "<frozen importlib._bootstrap_external>", line 896, in get_code
  File "<frozen importlib._bootstrap_external>", line 826, in source_to_code
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "/var/home/Alen/Desktop/SolarEx/solarex/render/manager.py", line 167
    def __init__(self):
IndentationError: expected an indented block after function definition on line 166
