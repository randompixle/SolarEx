FIX THE CODE that is causeing this ishue on my computer:

Alen@bazzite:~/Desktop/ReExplore$ python3 solarx.py
[SolarEx] Booting modular web system…
[SolarEx] Using profile: <Profile Default incognito=False>
[SolarEx] Loaded module 'net' from 'solarex.net'
/usr/lib/python3.14/site-packages/anyio/from_thread.py:119: SyntaxWarning: 'return' in a 'finally' block
  return result
[SolarEx] Module 'net' already registered, replacing.
[SolarEx] Loaded module 'net' from 'solarex.net.httpx_backend'
[SolarEx] Loaded module 'render' from 'solarex.render.manager'
[SolarEx] Renderer set to 'qtweb'
[SolarEx] Loaded module 'ui' from 'solarex.ui'
[SolarEx] Module 'ui' already registered, replacing.
[SolarEx] Loaded module 'ui' from 'solarex.ui.classic'
[SolarEx][plugin] Loaded AboutSolarEx
[DarkMode] Enabled (CSS inject via extensions if configured)
[SolarEx][plugin] Loaded DarkMode
[DemoUI] Plugin active.
[SolarEx][plugin] Loaded DemoUI
[HelloEx] Registered about:helloex
[SolarEx][plugin] Loaded HelloEx
[Logger] Ready.
[SolarEx][plugin] Loaded Logger
[PluginDocs] Ready!
[SolarEx][plugin] Loaded PluginDocs
[SolarEx][plugin] Loaded PluginForge
[RendererSettings] Ready
[SolarEx][plugin] Loaded RendererSettings
Traceback (most recent call last):
  File "/var/home/Alen/Desktop/ReExplore/solarx.py", line 65, in <module>
    main()
    ~~~~^^
  File "/var/home/Alen/Desktop/ReExplore/solarx.py", line 52, in main
    win = win_cls(core, start_url=args.home)
  File "/var/home/Alen/Desktop/ReExplore/solarex/ui/classic.py", line 36, in __init__
    self.open_tab(start_url or "https://www.google.com/")
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/home/Alen/Desktop/ReExplore/solarex/ui/classic.py", line 39, in open_tab
    view = self.core.render.new_view()
  File "/var/home/Alen/Desktop/ReExplore/solarex/Plugins/Logger/main.py", line 5, in hooked_view
    view = old_new_view(*a, **kw)
  File "/var/home/Alen/Desktop/ReExplore/solarex/Plugins/HelloEx/main.py", line 6, in patched_view
    view = old_view(*a, **kw)
  File "/var/home/Alen/Desktop/ReExplore/solarex/render/manager.py", line 28, in new_view
    return backend.new_view(self.core, *a, **kw)
           ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/var/home/Alen/Desktop/ReExplore/solarex/render/manager.py", line 42, in new_view
    from PyQt6.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
ImportError: cannot import name 'QWebEnginePage' from 'PyQt6.QtWebEngineWidgets' (/home/Alen/.local/lib/python3.14/site-packages/PyQt6/QtWebEngineWidgets.abi3.so). Did you mean: 'QtWebEngineCore'?
Alen@bazzite:~/Desktop/ReExplore$ 
