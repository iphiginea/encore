from pathlib import Path
import re

path = Path('index.html')
s = path.read_text()
worker = 'https://encore-setlist-proxy.kiah-harpool.workers.dev'

# Replace API credential setup in Settings with a simple close control.
settings_pattern = re.compile(
    r'    <h2 class="display">setlist\.fm API Key</h2>.*?'
    r'    </div>\n\n'
    r'    <div class="settings-section">',
    re.S,
)
settings_replacement = '''    <h2 class="display">Settings</h2>
    <div class="row">
      <button class="cancel" id="settings-cancel">Close</button>
    </div>

    <div class="settings-section">'''
s, n = settings_pattern.subn(settings_replacement, s, count=1)
if n != 1:
    raise SystemExit('Could not replace setlist.fm settings controls')

# Add the fixed Worker URL and remove browser credential state.
ticket_line = "const TICKET_COLORS = ['#e8734a','#7ba05b','#5b8fa3','#d4a017','#9b7fb8','#d67a94','#4a9b8e','#c25b3f'];\n"
if ticket_line not in s:
    raise SystemExit('Could not find TICKET_COLORS anchor')
s = s.replace(ticket_line, ticket_line + f"const SETLIST_PROXY_URL = '{worker}';\n", 1)
s = s.replace("  apiKey: null,\n  proxyUrl: null,\n", "", 1)

# Stop loading credentials from localStorage and delete old saved values on next load.
old_init = "  const key = await storageGet('encore:api-key');\n  if(key) state.apiKey = key;\n  const proxyUrl = await storageGet('encore:proxyurl');\n  if(proxyUrl) state.proxyUrl = proxyUrl;\n"
new_init = "  try{ localStorage.removeItem('encore:api-key'); localStorage.removeItem('encore:proxyurl'); }catch(e){}\n"
if old_init not in s:
    raise SystemExit('Could not find Encore credential init block')
s = s.replace(old_init, new_init, 1)

# Settings no longer save or display API credentials.
s = s.replace("  el('settings-save').onclick = saveApiKey;\n", "", 1)
old_open = "function openSettings(){\n  el('api-key-input').value = state.apiKey || '';\n  el('proxy-url-input').value = state.proxyUrl || '';\n  renderVenueSizeList();\n  el('settings-modal').classList.remove('hidden');\n}\n"
new_open = "function openSettings(){\n  renderVenueSizeList();\n  el('settings-modal').classList.remove('hidden');\n}\n"
if old_open not in s:
    raise SystemExit('Could not find openSettings credential block')
s = s.replace(old_open, new_open, 1)
s, n = re.subn(
    r"\nasync function saveApiKey\(\)\{.*?\n\}\n\nfunction escapeHtml",
    "\nfunction escapeHtml",
    s,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit('Could not remove saveApiKey')

# Search no longer depends on browser credentials.
search_checks = '''  if(!state.apiKey){
    el('search-status').innerHTML = `<div class="inline-msg warn">Add your setlist.fm API key first — tap the ⚙ up top.</div>`;
    return;
  }
  if(!state.proxyUrl){
    el('search-status').innerHTML = `<div class="inline-msg warn">setlist.fm blocks direct requests from a browser — you need to set up the free proxy first. See Settings for steps.</div>`;
    return;
  }
'''
if search_checks not in s:
    raise SystemExit('Could not find runSearch credential checks')
s = s.replace(search_checks, "", 1)

s = s.replace("`${state.proxyUrl}/rest/1.0/search/setlists?artistName=", "`${SETLIST_PROXY_URL}/rest/1.0/search/setlists?artistName=", 1)
s = s.replace("const res = await fetch(url, { headers: { 'x-api-key': state.apiKey, 'Accept': 'application/json' } });", "const res = await fetch(url, { headers: { 'Accept': 'application/json' } });", 1)
s = s.replace("setlist.fm rejected that request. Check your API key in settings.", "Encore could not load shows from setlist.fm.", 1)
s = s.replace("Couldn't reach the proxy. Double-check the proxy URL in Settings.", "Couldn't reach the show data service. Try again in a moment.", 1)

# Setlist detail requests also use the Worker without exposing the key.
old_fetch_songs = '''async function fetchSetlistSongs(setlistId){
  if(!state.proxyUrl || !state.apiKey) return null;
  try{
    const res = await fetch(`${state.proxyUrl}/rest/1.0/setlist/${setlistId}`, { headers: { 'x-api-key': state.apiKey, 'Accept': 'application/json' } });
    if(!res.ok) return null;
    const data = await res.json();
    return extractSongs(data);
  }catch(e){ return null; }
}
'''
new_fetch_songs = '''async function fetchSetlistSongs(setlistId){
  try{
    const res = await fetch(`${SETLIST_PROXY_URL}/rest/1.0/setlist/${setlistId}`, { headers: { 'Accept': 'application/json' } });
    if(!res.ok) return null;
    const data = await res.json();
    return extractSongs(data);
  }catch(e){ return null; }
}
'''
if old_fetch_songs not in s:
    raise SystemExit('Could not find fetchSetlistSongs credential request')
s = s.replace(old_fetch_songs, new_fetch_songs, 1)

backfill_guard = '''  if(!state.apiKey || !state.proxyUrl){
    el('backfill-status').textContent = 'Add your API key and proxy URL above first.';
    return;
  }
'''
if backfill_guard not in s:
    raise SystemExit('Could not find backfill credential guard')
s = s.replace(backfill_guard, "", 1)

# Safety checks: no browser credential machinery may remain.
for forbidden in [
    'state.apiKey',
    'state.proxyUrl',
    "'x-api-key': state.apiKey",
    'api-key-input',
    'proxy-url-input',
    'settings-save',
    'saveApiKey',
]:
    if forbidden in s:
        raise SystemExit(f'Browser credential reference still present: {forbidden}')
if worker not in s:
    raise SystemExit('Encore Worker URL was not added')

path.write_text(s)
