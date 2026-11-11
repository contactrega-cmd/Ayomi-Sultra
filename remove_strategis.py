import os
import shutil

BASE_DIR = "/Users/regaprasetyo/.gemini/antigravity/scratch/ews-inflasi-dashboard"
BUILD_FILE = os.path.join(BASE_DIR, "build_index_html.py")
BACKUP_FILE = os.path.join(BASE_DIR, "build_index_html.py.pre_remove_strategis")

shutil.copyfile(BUILD_FILE, BACKUP_FILE)
print(f"Created backup at {BACKUP_FILE}")

with open(BUILD_FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Lighten ews_alps_str header
h_target = '''EWS_ALPS_JSON_PATH = os.path.join(DATA_DIR, "ews_alps_matrix.json")
ews_alps_data = {}
if os.path.exists(EWS_ALPS_JSON_PATH):
    with open(EWS_ALPS_JSON_PATH, "r", encoding="utf-8") as f:
        ews_alps_data = json.load(f)
ews_alps_str = json.dumps(ews_alps_data, ensure_ascii=False)'''

h_replacement = '''# EWS ALPS matriks lama (Informasi Strategis) ditiadakan untuk meringankan beban hitung dashboard
ews_alps_str = "{}"'''

assert h_target in content, "Error: Header ews_alps_str target not found!"
content = content.replace(h_target, h_replacement, 1)
print("1. ews_alps_str lightened to '{}'.")

# 2. Desktop navbar: update Logo link & Beranda link, and remove topNavInformasiStrategisWrapper
logo_target = '''onclick="switchDashboardTab('ews'); navigateToEwsSubmenu('portal');" class="flex items-center gap-3 text-slate-800 focus:outline-none select-none group"'''
logo_replacement = '''onclick="switchDashboardTab('ews');" class="flex items-center gap-3 text-slate-800 focus:outline-none select-none group"'''
assert logo_target in content, "Error: Logo target not found!"
content = content.replace(logo_target, logo_replacement, 1)
print("2a. Logo link updated.")

nav_block_start = content.find('<!-- 1. Beranda (Direct Tab to Executive Landing Portal) -->')
nav_alps_marker = content.find('<!-- 3. Peringatan Dini Harga (ALPS 17 Kab/Kota) -->')
assert nav_block_start != -1 and nav_alps_marker != -1, "Error: Nav block markers not found!"

nav_old_chunk = content[nav_block_start:nav_alps_marker]
nav_new_chunk = '''<!-- 1. Beranda -->
        <button 
          id="navBtn_ews" 
          onclick="switchDashboardTab('ews')" 
          class="h-full px-2.5 lg:px-3.5 flex items-center justify-center text-xs lg:text-sm font-black text-blue-900 border-b-[3px] border-blue-900 transition-colors cursor-pointer select-none whitespace-nowrap"
        >
          <span class="whitespace-nowrap">Beranda</span>
        </button>

        '''
content = content[:nav_block_start] + nav_new_chunk + content[nav_alps_marker:]
print("2b. Desktop nav Informasi Strategis removed.")

# 3. Mobile navbar: remove Informasi Strategis accordion
mnav_start = content.find('<!-- 1. Beranda (Portal) -->')
mnav_alps = content.find('<button id="mobileNavBtn_alps"')
assert mnav_start != -1 and mnav_alps != -1, "Error: Mobile nav markers not found!"

mnav_old_chunk = content[mnav_start:mnav_alps]
mnav_new_chunk = '''<!-- 1. Beranda -->
        <button id="mobileNavBtn_ews" onclick="switchDashboardTab('ews'); toggleMobileTopNavbar();" class="w-full text-left py-2.5 px-3 rounded-xl text-sm font-extrabold text-blue-900 bg-blue-50 border border-blue-200/80 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span>🏠</span>
            <span>Beranda</span>
          </div>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-200/70 text-blue-900">Portal</span>
        </button>

        '''
content = content[:mnav_start] + mnav_new_chunk + content[mnav_alps:]
print("3. Mobile nav Informasi Strategis removed.")

# 4. Beranda Portal Cards (replace with 3 core dashboard gateways)
cards_start = content.find('<!-- 3 Kartu Menu Utama Interaktif (Persis Format Desain Data Pangan Indonesia) -->')
cards_end = content.find('<!-- Sub Menu Navigator Bar di Atas Matriks EWS')
assert cards_start != -1 and cards_end != -1, "Error: Beranda cards markers not found!"

cards_new = '''<!-- 3 Kartu Menu Utama Interaktif (Pintu Gerbang Dashboard) -->
              <div class="grid grid-cols-1 md:grid-cols-3 gap-5">

                <!-- KARTU MENU 1: PERINGATAN DINI HARGA (ALPS 17 KAB/KOTA) -->
                <div 
                  onclick="switchDashboardTab('alps')" 
                  class="bg-white border-2 border-slate-200/90 hover:border-rose-500 rounded-3xl p-5 shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer flex flex-col justify-between group relative overflow-hidden"
                >
                  <div class="space-y-4">
                    <div class="flex items-center gap-3.5">
                      <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-rose-500 via-rose-600 to-red-600 flex items-center justify-center text-3xl shadow-md group-hover:scale-105 transition-transform duration-300 flex-shrink-0 text-white">
                        ⚡
                      </div>
                      <div class="min-w-0">
                        <h3 class="text-base sm:text-lg font-black text-slate-900 group-hover:text-rose-700 transition tracking-tight">
                          Peringatan Dini Harga (ALPS)
                        </h3>
                        <div class="text-[11px] font-bold text-rose-600">17 Kab/Kota Se-Sultra</div>
                      </div>
                    </div>

                    <p class="text-xs text-slate-600 leading-relaxed">
                      Sistem Peringatan Dini (EWS ALPS) berbasis <strong>Regresi Tren Linier &amp; 12 Variabel Dummy Musiman Bulanan</strong> mencakup seluruh 17 kabupaten/kota se-Sultra terintegrasi PIHPS BI dan SP2KP Kemendag RI.
                    </p>
                  </div>

                  <div class="pt-5 mt-4 border-t border-slate-100 flex items-center justify-between">
                    <span class="text-xs font-black text-rose-600 group-hover:text-rose-800 flex items-center gap-1.5">
                      <span>Buka Matriks ALPS 17 Kab/Kota</span>
                      <span class="text-base group-hover:translate-x-1 transition-transform">&rarr;</span>
                    </span>
                    <span class="w-8 h-8 rounded-full bg-rose-50 group-hover:bg-rose-600 text-rose-600 group-hover:text-white flex items-center justify-center transition-colors">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"></path></svg>
                    </span>
                  </div>
                </div>

                <!-- KARTU MENU 2: PERKEMBANGAN INFLASI -->
                <div 
                  onclick="switchDashboardTab('inflasi')" 
                  class="bg-white border-2 border-slate-200/90 hover:border-blue-500 rounded-3xl p-5 shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer flex flex-col justify-between group relative overflow-hidden"
                >
                  <div class="space-y-4">
                    <div class="flex items-center gap-3.5">
                      <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 flex items-center justify-center text-3xl shadow-md group-hover:scale-105 transition-transform duration-300 flex-shrink-0 text-white">
                        📈
                      </div>
                      <div class="min-w-0">
                        <h3 class="text-base sm:text-lg font-black text-slate-900 group-hover:text-blue-700 transition tracking-tight">
                          Perkembangan Inflasi Daerah
                        </h3>
                        <div class="text-[11px] font-bold text-blue-600">Rilis Resmi BPS Sultra</div>
                      </div>
                    </div>

                    <p class="text-xs text-slate-600 leading-relaxed">
                      Analisis pergerakan inflasi historis YoY &amp; MtM Provinsi Sulawesi Tenggara, 4 kabupaten/kota IHK (Kendari, Baubau, Kolaka, Konawe), dan 11 kelompok pengeluaran masyarakat.
                    </p>
                  </div>

                  <div class="pt-5 mt-4 border-t border-slate-100 flex items-center justify-between">
                    <span class="text-xs font-black text-blue-600 group-hover:text-blue-800 flex items-center gap-1.5">
                      <span>Buka Analisis Inflasi BPS</span>
                      <span class="text-base group-hover:translate-x-1 transition-transform">&rarr;</span>
                    </span>
                    <span class="w-8 h-8 rounded-full bg-blue-50 group-hover:bg-blue-600 text-blue-600 group-hover:text-white flex items-center justify-center transition-colors">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"></path></svg>
                    </span>
                  </div>
                </div>

                <!-- KARTU MENU 3: PETA SEBARAN HARGA & KAD -->
                <div 
                  onclick="switchDashboardTab('komoditas')" 
                  class="bg-white border-2 border-slate-200/90 hover:border-emerald-500 rounded-3xl p-5 shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer flex flex-col justify-between group relative overflow-hidden"
                >
                  <div class="space-y-4">
                    <div class="flex items-center gap-3.5">
                      <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 flex items-center justify-center text-3xl shadow-md group-hover:scale-105 transition-transform duration-300 flex-shrink-0 text-white">
                        🛍️
                      </div>
                      <div class="min-w-0">
                        <h3 class="text-base sm:text-lg font-black text-slate-900 group-hover:text-emerald-700 transition tracking-tight">
                          Peta Sebaran Harga Pangan
                        </h3>
                        <div class="text-[11px] font-bold text-emerald-600">PIHPS BI &amp; SP2KP Kemendag</div>
                      </div>
                    </div>

                    <p class="text-xs text-slate-600 leading-relaxed">
                      Pemantauan spasial harga 10 komoditas strategis harian, filter tanggal historis, deteksi disparitas surplus/defisit, serta simulasi Kerjasama Antar Daerah (KAD).
                    </p>
                  </div>

                  <div class="pt-5 mt-4 border-t border-slate-100 flex items-center justify-between">
                    <span class="text-xs font-black text-emerald-600 group-hover:text-emerald-800 flex items-center gap-1.5">
                      <span>Buka Peta Sebaran Harga</span>
                      <span class="text-base group-hover:translate-x-1 transition-transform">&rarr;</span>
                    </span>
                    <span class="w-8 h-8 rounded-full bg-emerald-50 group-hover:bg-emerald-600 text-emerald-600 group-hover:text-white flex items-center justify-center transition-colors">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"></path></svg>
                    </span>
                  </div>
                </div>

              </div>

            </div>
'''
content = content[:cards_start] + cards_new + content[cards_end:]
print("4. Beranda gateway cards updated.")

# 5. Remove matriksVF_section, matriks10_section, matriksClimate_section, ews4kRecommendation_container
subsections_start = content.find('<!-- Sub Menu Navigator Bar di Atas Matriks EWS')
tab_inflasi_marker = content.find('<!-- ================= TAB 1: PERKEMBANGAN INFLASI ================= -->')
assert subsections_start != -1 and tab_inflasi_marker != -1, "Error: Subsections markers not found!"

clean_tab_ews_end = '''          </section>

          '''
content = content[:subsections_start] + clean_tab_ews_end + content[tab_inflasi_marker:]
print("5. 750 lines of matriksVF, matriks10, matriksClimate, and ews4k removed from DOM.")

# 6. Clean up switchDashboardTab
s_target = '''      if (tabId === "ews") {{
        renderEwsAlpsMatrix();
        if (currentEwsSubmenu === "portal" || !currentEwsSubmenu) {{
          navigateToEwsSubmenu("portal");
        }} else {{
          navigateToEwsSubmenu(currentEwsSubmenu);
        }}
      }} else if (tabId === "alps") {{'''

s_replacement = '''      if (tabId === "ews") {{
        updateEwsPortalKpiCards();
      }} else if (tabId === "alps") {{'''

assert s_target in content, "Error: switchDashboardTab target not found!"
content = content.replace(s_target, s_replacement, 1)

# Remove updateTopNavActiveStates and subnav styling in switchDashboardTab
topnav_target = '''      // Perbarui status aktif navigasi Menu Utama & Informasi Strategis
      updateTopNavActiveStates();

      // Penyesuaian submenu styling EWS saat berpindah tab non-EWS
      if (tabId !== "ews") {{
        const subKeys = ["vf", "pangan", "iklim"];
        subKeys.forEach(k => {{
          const subBtn = document.getElementById("subnavBtn_ews_" + k);
          const mobileSubBtn = document.getElementById("mobileSubnavBtn_" + k);
          if (subBtn) subBtn.className = "w-full text-left p-2.5 rounded-xl hover:bg-slate-50 text-xs font-semibold text-slate-700 hover:text-blue-900 transition flex items-center gap-2.5 cursor-pointer group/item";
          if (mobileSubBtn) mobileSubBtn.className = "w-full text-left py-1.5 px-2.5 rounded-lg text-slate-600 hover:text-blue-900 hover:bg-slate-50 flex items-center gap-2 font-medium";
        }});
      }}'''

topnav_replacement = '''      // Update URL hash
      if (window.history && window.history.replaceState) {{
        window.history.replaceState(null, "", "#" + tabId);
      }}'''

assert topnav_target in content, "Error: topnav_target in switchDashboardTab not found!"
content = content.replace(topnav_target, topnav_replacement, 1)
print("6. switchDashboardTab cleaned up.")

# 7. Stub out navigateToEwsSubmenu, toggleStrategisTabClick, and updateTopNavActiveStates
sub_funcs_target = '''    let activeDashboardTab = "ews";
    let currentEwsSubmenu = "portal";

    function navigateToEwsSubmenu(mode) {'''

# Find the end of updateTopNavActiveStates
idx_nav_func = content.find('function navigateToEwsSubmenu(mode) {{')
idx_switch_func = content.find('function switchDashboardTab(tabId) {{')
assert idx_nav_func != -1 and idx_switch_func != -1, "Error: Function markers not found!"

clean_sub_funcs = '''    let activeDashboardTab = "ews";
    let currentEwsSubmenu = "portal";

    function navigateToEwsSubmenu(mode) {{
      switchDashboardTab("ews");
    }}

    function toggleStrategisTabClick() {{
      switchDashboardTab("ews");
    }}

    function updateTopNavActiveStates() {{}}

    '''

content = content[:idx_nav_func] + clean_sub_funcs + content[idx_switch_func:]
print("7. Submenu routing functions stubbed/removed.")

# 8. Clean up unused matrix rendering functions
# renderEwsAlpsMatrix10, renderEwsAlpsMatrixVF, renderEwsAlpsMatrixClimate, etc.
idx_matrix10 = content.find('function renderEwsAlpsMatrix10() {{')
idx_filterVF = content.find('function filterEwsTableVF(query) {{')
idx_gen_rec = content.find('function generateExecutiveRecommendations(isManualClick = false) {{')
assert idx_matrix10 != -1 and idx_gen_rec != -1, "Error: Matrix render markers not found!"

# We can replace the renderEwsAlpsMatrix functions from idx_matrix10 to the end of tooltip functions
idx_tooltip_end = content.find('function generateExecutiveRecommendations')
assert idx_tooltip_end != -1, "Error: generateExecutiveRecommendations marker not found!"

matrix_clean_stubs = '''    // Matriks Informasi Strategis ditiadakan untuk meringankan beban hitung dashboard
    function renderEwsAlpsMatrix10() {{}}
    function renderEwsAlpsMatrixVF() {{}}
    function renderEwsAlpsMatrixClimate() {{}}
    function renderEwsAlpsMatrixTop5() {{}}
    function renderEwsAlpsMatrix() {{}}
    function updateEwsDropdown10UI() {{}}
    function updateEwsDropdownVFUI() {{}}
    function updateEwsDropdownClimateUI() {{}}
    function showEwsTooltip10() {{}}
    function showEwsTooltipVF() {{}}
    function showEwsTooltipClimate() {{}}
    function moveEwsTooltip() {{}}
    function hideEwsTooltip() {{}}

    '''

content = content[:idx_matrix10] + matrix_clean_stubs + content[idx_tooltip_end:]
print("8. Unused matrix calculation and rendering loops removed.")

# 9. Clean up initDashboard()
init_old = '''        const hash = window.location.hash ? window.location.hash.substring(1) : "";
        if (hash.startsWith("ews-")) {{
          const sub = hash.replace("ews-", "");
          switchDashboardTab("ews");
          navigateToEwsSubmenu(sub);
        }} else {{
          const initialTab = ["ews", "alps", "inflasi", "komoditas", "iklim", "kad"].includes(hash) ? hash : "ews";
          switchDashboardTab(initialTab);
        }}
        updateEwsDropdown10UI();
        updateEwsDropdownVFUI();
        updateEwsDropdownClimateUI();
        renderEwsAlpsMatrix();
        renderAlps17MatrixModule();
        updateExecutiveRecommendations();
        updateEwsPortalKpiCards();'''

init_new = '''        const hash = window.location.hash ? window.location.hash.substring(1) : "";
        if (hash.startsWith("ews-")) {{
          switchDashboardTab("ews");
        }} else {{
          const initialTab = ["ews", "alps", "inflasi", "komoditas", "iklim", "kad"].includes(hash) ? hash : "ews";
          switchDashboardTab(initialTab);
        }}
        renderAlps17MatrixModule();
        updateEwsPortalKpiCards();'''

assert init_old in content, "Error: init_old not found!"
content = content.replace(init_old, init_new, 1)
print("9. initDashboard() cleaned up.")

with open(BUILD_FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully processed {BUILD_FILE}!")
