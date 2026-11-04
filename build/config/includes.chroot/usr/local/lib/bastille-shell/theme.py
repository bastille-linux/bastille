"""Bastille shell — glass theme."""

CSS = """
window.shell, window.shell.background { background: none; background-color: transparent; }
window.shell.catcher { background: rgba(0,0,0,0.0); }
window.shell.catcher.dim { background: rgba(0,0,0,0.28); }
.glass { background: rgba(30,35,33,0.70); border: 1px solid rgba(255,255,255,0.16);
         border-radius: 22px; }
.glass-soft { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.10);
              border-radius: 18px; }
label { color: #f4f6f5; }
.dim { color: rgba(244,246,245,0.62); }
.small { font-size: 11px; }
.title { font-weight: 700; font-size: 15px; }
.big { font-size: 28px; font-weight: 300; }

/* ── motion ─────────────────────────────────────────────────────────────── */
@keyframes popin {
    from { opacity: 0; transform: translateY(-10px) scale(0.965); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes slidein {
    from { opacity: 0; transform: translateX(40px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes bounce {
    0%   { transform: translateY(0); }
    22%  { transform: translateY(-20px); }
    44%  { transform: translateY(0); }
    62%  { transform: translateY(-9px); }
    80%  { transform: translateY(0); }
    90%  { transform: translateY(-3px); }
    100% { transform: translateY(0); }
}
@keyframes wiggle {
    from { transform: rotate(-1.1deg); }
    to   { transform: rotate(1.1deg); }
}
.popin { animation-name: popin; animation-duration: 200ms; animation-timing-function: cubic-bezier(0.2, 0.9, 0.3, 1);
         animation-fill-mode: both; }
.popin.closing { animation: none; opacity: 0; transition: opacity 140ms ease-in; }
.bounce { animation-name: bounce; animation-duration: 700ms; animation-timing-function: ease-out; }
.wiggle { animation-name: wiggle; animation-duration: 150ms; animation-timing-function: ease-in-out;
          animation-iteration-count: infinite; animation-direction: alternate; }

/* top bar */
.bar { background: linear-gradient(to bottom, rgba(16,22,19,0.78), rgba(16,22,19,0.58));
       border-bottom: 1px solid rgba(255,255,255,0.07); min-height: 28px; padding: 0 10px; }
.bar label { font-size: 13px; }
.bar .app { font-weight: 700; }
.barbtn { background: transparent; background-image: none; border: none; box-shadow: none;
          border-radius: 7px; padding: 0 8px; min-height: 22px; color: #f4f6f5;
          transition: background 120ms ease; }
.barbtn:hover, .barbtn.active { background: rgba(255,255,255,0.16); }
.barbtn:active { background: rgba(255,255,255,0.24); }

/* dock */
.dock { background: rgba(30,35,33,0.62); border: 1px solid rgba(255,255,255,0.20);
        border-radius: 28px; padding: 7px 12px; }
.dockbtn { background: transparent; background-image: none; border: none; box-shadow: none;
           border-radius: 16px; padding: 4px; min-width: 0; min-height: 0;
           transition: transform 160ms cubic-bezier(0.2, 0.9, 0.3, 1.2), background 160ms ease; }
.dockbtn:hover { background: rgba(255,255,255,0.14); transform: scale(1.14) translateY(-3px); }
.dockbtn:active { transform: scale(0.94); }
.dot { min-width: 4px; min-height: 4px; border-radius: 2px; background: rgba(255,255,255,0.9); }
.dock-sep { min-width: 1px; background: rgba(255,255,255,0.22); margin: 8px 6px; }

/* menus (Apple-style menu, context menus) */
.menu { background: rgba(38,44,41,0.88); border: 1px solid rgba(255,255,255,0.16); border-radius: 12px;
        padding: 5px; box-shadow: 0 12px 36px rgba(0,0,0,0.5); }
.menuitem { background: transparent; background-image: none; border: none; box-shadow: none;
            border-radius: 6px; padding: 4px 12px; min-height: 24px; }
.menuitem:hover { background: #2a78d6; }
.menuitem label { font-size: 13px; }
.menuitem .hint { color: rgba(244,246,245,0.5); font-size: 12px; }
.menusep { min-height: 1px; background: rgba(255,255,255,0.12); margin: 5px 8px; }
.submenu { padding: 2px 0 2px 12px; }
.chev { transition: transform 160ms ease; }
.chev.open { transform: rotate(90deg); }

/* dialogs */
.dialog { background: rgba(40,46,43,0.94); border: 1px solid rgba(255,255,255,0.16); border-radius: 18px;
          padding: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.55); }
.fqrow { background: transparent; background-image: none; border: none; box-shadow: none; border-radius: 8px;
         padding: 6px 10px; }
.fqrow:hover { background: rgba(255,255,255,0.10); }
.fqrow.sel { background: #2a78d6; }
.kv label.dim { font-size: 12px; }

/* spotlight launcher */
.spot { background: rgba(44,50,47,0.86); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 40px; padding: 0 26px; }
.spot entry, .spot entry text { background: transparent; color: #f6f8f7; font-size: 24px;
                                border: none; box-shadow: none; outline: none; }
.circlebtn { min-width: 62px; min-height: 62px; border-radius: 31px; padding: 0;
             background: rgba(48,54,51,0.88); border: 1px solid rgba(255,255,255,0.14);
             background-image: none; box-shadow: 0 8px 24px rgba(0,0,0,0.4);
             transition: background 140ms ease, transform 140ms ease; }
.circlebtn:hover { background: rgba(70,78,74,0.92); transform: scale(1.05); }
.circlebtn.sel { background: rgba(42,120,214,0.9); border-color: rgba(255,255,255,0.35); }
.results { background: rgba(44,50,47,0.90); border: 1px solid rgba(255,255,255,0.12);
           border-radius: 26px; padding: 8px; }
.resrow { background: transparent; background-image: none; border: none; box-shadow: none;
          border-radius: 14px; padding: 8px 12px; }
.resrow:hover, .resrow.sel { background: rgba(255,255,255,0.14); }
.resrow.sel { background: rgba(42,120,214,0.75); }
.gridbtn { background: transparent; background-image: none; border: none; box-shadow: none;
           border-radius: 18px; padding: 10px; transition: background 140ms ease, transform 140ms ease; }
.gridbtn:hover { background: rgba(255,255,255,0.14); }
.gridbtn:active { transform: scale(0.95); }

/* notification centre + widgets */
.nc { background: rgba(26,31,29,0.80); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 24px; padding: 14px; }
.ncard { background: rgba(70,76,73,0.62); border: 1px solid rgba(255,255,255,0.10);
         border-radius: 18px; padding: 12px 14px; }
.sechead { font-weight: 700; font-size: 15px; }
.pill { background: rgba(80,86,83,0.80); border: 1px solid rgba(255,255,255,0.14); border-radius: 18px;
        padding: 6px 14px; background-image: none; box-shadow: none; min-height: 22px;
        transition: background 140ms ease; }
.pill:hover { background: rgba(110,118,114,0.88); }
.pill.pri { background: #2a78d6; border-color: #2a78d6; font-weight: 600; }
.pill.pri:hover { background: #3385e3; }
.pill.danger { background: #d8453c; border-color: #d8453c; font-weight: 600; }
.pill.danger:hover { background: #e5564d; }
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
.badge { min-width: 20px; min-height: 20px; border-radius: 10px; padding: 0; background-image: none;
         box-shadow: none; border: 2px solid rgba(26,31,29,1); }
.badge.minus { background: #e5483f; }
.badge.plus { background: #2fb457; }
.badge.mv { background: rgba(90,96,93,0.95); }
.addtile { background: rgba(255,255,255,0.06); border: 2px dashed rgba(255,255,255,0.28); border-radius: 22px;
           background-image: none; box-shadow: none; min-height: 60px; }
.addtile:hover { background: rgba(255,255,255,0.12); }

/* control centre */
.cc { background: rgba(26,31,29,0.80); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 26px; padding: 12px; }
.tile { background: rgba(70,76,73,0.62); border: 1px solid rgba(255,255,255,0.10); border-radius: 20px;
        padding: 8px 10px; }
.tilecircle { min-width: 38px; min-height: 38px; border-radius: 19px; padding: 0; background-image: none;
              background: rgba(255,255,255,0.16); border: none; box-shadow: none;
              transition: background 160ms ease; }
.tilecircle:hover { background: rgba(255,255,255,0.26); }
.tile.on .tilecircle { background: #2a78d6; }
.tile.on .tilecircle:hover { background: #3a88e6; }
.tilebody { background: transparent; background-image: none; border: none; box-shadow: none; padding: 2px 4px;
            border-radius: 12px; }
.tilebody:hover { background: rgba(255,255,255,0.08); }
.slidebox { background: rgba(70,76,73,0.62); border: 1px solid rgba(255,255,255,0.10); border-radius: 20px;
            padding: 10px 14px; }
.netrow { background: transparent; background-image: none; border: none; box-shadow: none; border-radius: 10px;
          padding: 6px 8px; transition: background 120ms ease; }
.netrow:hover { background: rgba(255,255,255,0.10); }
.netcircle { min-width: 30px; min-height: 30px; border-radius: 15px; background: rgba(255,255,255,0.16); }
.netcircle.on { background: #2a78d6; }
.group { background: rgba(70,76,73,0.50); border: 1px solid rgba(255,255,255,0.10); border-radius: 16px;
         padding: 4px; }
.sep { min-height: 1px; background: rgba(255,255,255,0.10); margin: 0 10px; }
.cc entry { background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.16); border-radius: 10px;
            color: #f4f6f5; min-height: 30px; padding: 0 8px; box-shadow: none; }
switch { background: rgba(255,255,255,0.22); border: none; border-radius: 16px; min-width: 44px; min-height: 26px;
         outline: none; box-shadow: none; }
switch:checked { background: #2a78d6; }
switch slider { background: #ffffff; border-radius: 13px; min-width: 22px; min-height: 22px; margin: 2px;
                border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.4); }
.toast { background: rgba(36,41,39,0.92); border: 1px solid rgba(255,255,255,0.16); border-radius: 18px;
         padding: 12px 14px; animation-name: slidein; animation-duration: 260ms;
         animation-timing-function: cubic-bezier(0.2, 0.9, 0.3, 1); animation-fill-mode: both; }
scale { outline: none; padding: 0; }
scale trough { background: rgba(255,255,255,0.18); border: none; border-radius: 12px; min-height: 22px; outline: none; }
scale highlight { background: rgba(255,255,255,0.92); border-radius: 12px; }
scale slider { min-width: 2px; min-height: 2px; margin: 0; background: transparent; border: none; box-shadow: none; outline: none; }
textview, textview text { background: transparent; color: #f4f6f5; }
calendar { background: transparent; color: #f4f6f5; border: none; }
calendar:selected { background: #2a78d6; border-radius: 12px; }
"""
