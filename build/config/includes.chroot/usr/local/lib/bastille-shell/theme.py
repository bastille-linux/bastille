"""Bastille shell — glass theme."""

CSS = """
window.shell, window.shell.background { background: none; background-color: transparent; }
window.shell.catcher { background: rgba(0,0,0,0.0); }
.glass { background: rgba(30,35,33,0.70); border: 1px solid rgba(255,255,255,0.16);
         border-radius: 22px; }
.glass-soft { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.10);
              border-radius: 18px; }
label { color: #f4f6f5; }
.dim { color: rgba(244,246,245,0.62); }
.small { font-size: 11px; }
.title { font-weight: 700; font-size: 15px; }
.big { font-size: 28px; font-weight: 300; }

/* top bar */
.bar { background: linear-gradient(to bottom, rgba(16,22,19,0.78), rgba(16,22,19,0.58));
       border-bottom: 1px solid rgba(255,255,255,0.07); min-height: 28px; padding: 0 10px; }
.bar label { font-size: 13px; }
.bar .app { font-weight: 700; }
.barbtn { background: transparent; background-image: none; border: none; box-shadow: none;
          border-radius: 7px; padding: 0 8px; min-height: 22px; color: #f4f6f5; }
.barbtn:hover, .barbtn.active { background: rgba(255,255,255,0.16); }

/* dock */
.dock { background: rgba(30,35,33,0.62); border: 1px solid rgba(255,255,255,0.20);
        border-radius: 28px; padding: 7px 12px; }
.dockbtn { background: transparent; background-image: none; border: none; box-shadow: none;
           border-radius: 16px; padding: 4px; min-width: 0; min-height: 0; }
.dockbtn:hover { background: rgba(255,255,255,0.16); }
.dot { min-width: 4px; min-height: 4px; border-radius: 2px; background: rgba(255,255,255,0.9); }
.dock-sep { min-width: 1px; background: rgba(255,255,255,0.22); margin: 8px 6px; }

/* spotlight launcher */
.spot { background: rgba(44,50,47,0.86); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 40px; padding: 0 26px; }
.spot entry, .spot entry text { background: transparent; color: #f6f8f7; font-size: 24px;
                                border: none; box-shadow: none; outline: none; }
.circlebtn { min-width: 62px; min-height: 62px; border-radius: 31px; padding: 0;
             background: rgba(48,54,51,0.88); border: 1px solid rgba(255,255,255,0.14);
             background-image: none; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.circlebtn:hover { background: rgba(70,78,74,0.92); }
.circlebtn.sel { background: rgba(42,120,214,0.9); border-color: rgba(255,255,255,0.35); }
.results { background: rgba(44,50,47,0.90); border: 1px solid rgba(255,255,255,0.12);
           border-radius: 26px; padding: 8px; }
.resrow { background: transparent; background-image: none; border: none; box-shadow: none;
          border-radius: 14px; padding: 8px 12px; }
.resrow:hover, .resrow.sel { background: rgba(255,255,255,0.14); }
.resrow.sel { background: rgba(42,120,214,0.75); }
.gridbtn { background: transparent; background-image: none; border: none; box-shadow: none;
           border-radius: 18px; padding: 10px; }
.gridbtn:hover { background: rgba(255,255,255,0.14); }

/* notification centre + widgets */
.nc { background: rgba(26,31,29,0.80); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 24px; padding: 14px; }
.ncard { background: rgba(70,76,73,0.62); border: 1px solid rgba(255,255,255,0.10);
         border-radius: 18px; padding: 12px 14px; }
.sechead { font-weight: 700; font-size: 15px; }
.pill { background: rgba(80,86,83,0.80); border: 1px solid rgba(255,255,255,0.14); border-radius: 18px;
        padding: 6px 14px; background-image: none; box-shadow: none; min-height: 22px; }
.pill:hover { background: rgba(110,118,114,0.88); }
.pill.pri { background: #2a78d6; border-color: #2a78d6; font-weight: 600; }
.pill.pri:hover { background: #3385e3; }
.widget { background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.12);
          border-radius: 22px; padding: 12px; }
.gallery { background: rgba(34,40,37,0.92); border: 1px solid rgba(255,255,255,0.16);
           border-radius: 28px; box-shadow: 0 20px 60px rgba(0,0,0,0.6); }
.sidebtn { background: transparent; background-image: none; border: none; box-shadow: none;
           border-radius: 12px; padding: 8px 12px; }
.sidebtn:hover { background: rgba(255,255,255,0.10); }
.sidebtn.sel { background: rgba(255,255,255,0.16); }
.search { background: rgba(255,255,255,0.10); border: 2px solid rgba(42,120,214,0.9); border-radius: 14px;
          padding: 0 8px; min-height: 36px; }
.search text, .search { color: #f4f6f5; }

/* control centre */
.cc { background: rgba(26,31,29,0.80); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 26px; padding: 12px; }
.tile { background: rgba(70,76,73,0.62); border: 1px solid rgba(255,255,255,0.10); border-radius: 20px;
        padding: 10px 12px; background-image: none; box-shadow: none; }
.tile:hover { background: rgba(95,102,98,0.72); }
.tile.on { background: rgba(255,255,255,0.88); }
.tile.on label { color: #1a1d1b; }
.toast { background: rgba(36,41,39,0.92); border: 1px solid rgba(255,255,255,0.16); border-radius: 18px;
         padding: 12px 14px; }
scale { outline: none; padding: 0; }
scale trough { background: rgba(255,255,255,0.18); border: none; border-radius: 12px; min-height: 22px; outline: none; }
scale highlight { background: rgba(255,255,255,0.92); border-radius: 12px; }
scale slider { min-width: 2px; min-height: 2px; margin: 0; background: transparent; border: none; box-shadow: none; outline: none; }
textview, textview text { background: transparent; color: #f4f6f5; }
calendar { background: transparent; color: #f4f6f5; border: none; }
calendar:selected { background: #2a78d6; border-radius: 12px; }
"""
