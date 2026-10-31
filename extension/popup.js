const $ = id => document.getElementById(id);
const DEFAULT_URL = 'https://kiqnfbglxp.apps.bot-hosting.cloud/annonce';
let annoncesDetectees = [];

function statut(message) { $('statut').textContent = message; }
function validerUrl(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && url.pathname.endsWith('/annonce'); }
  catch { return false; }
}
function configLocale() { return new Promise(resolve => chrome.storage.local.get(['serverUrl', 'apiKey'], resolve)); }

(async () => {
  const cfg = await configLocale();
  $('serverUrl').value = cfg.serverUrl || DEFAULT_URL;
  $('apiKey').value = cfg.apiKey || '';
})();

$('sauvegarder').addEventListener('click', async () => {
  const serverUrl = $('serverUrl').value.trim();
  const apiKey = $('apiKey').value.trim();
  if (!validerUrl(serverUrl)) return statut('Adresse HTTPS invalide : elle doit se terminer par /annonce.');
  await chrome.storage.local.set({ serverUrl, apiKey });
  statut('Configuration enregistrée localement.');
});

function afficher(annonces) {
  const resultats = $('resultats');
  resultats.replaceChildren();
  for (const annonce of annonces) {
    const item = document.createElement('div'); item.className = 'item';
    if (annonce.image) {
      const img = document.createElement('img'); img.src = annonce.image; img.alt = 'Photo de l’annonce';
      img.referrerPolicy = 'no-referrer';
      img.addEventListener('error', () => { img.remove(); });
      item.append(img);
    }
    const details = document.createElement('div'); details.className = 'details';
    const title = document.createElement('div'); title.textContent = annonce.titre;
    const price = document.createElement('div'); price.textContent = `${annonce.prix} €`;
    const link = document.createElement('a'); link.href = annonce.lien; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = 'Voir sur Vinted';
    details.append(title, price, link); item.append(details); resultats.append(item);
  }
}

$('scanner').addEventListener('click', async () => {
  $('envoyer').disabled = true;
  annoncesDetectees = [];
  statut('Analyse des annonces affichées…');
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https:\/\/(?:[a-z]{2}\.)?vinted\./i.test(tab.url || '')) {
      return statut('Ouvre d’abord une page Vinted dans cet onglet.');
    }
    const response = await chrome.tabs.sendMessage(tab.id, { type: 'VINTED_SCAN' });
    annoncesDetectees = response?.annonces || [];
    afficher(annoncesDetectees);
    $('envoyer').disabled = annoncesDetectees.length === 0;
    statut(`${annoncesDetectees.length} annonce(s) trouvée(s). Envoi uniquement sur clic.`);
  } catch (e) { statut('Impossible de scanner : actualise la page Vinted et réessaie.'); }
});

$('envoyer').addEventListener('click', async () => {
  if (!annoncesDetectees.length) return;
  $('envoyer').disabled = true;
  const { serverUrl, apiKey } = await configLocale();
  if (!validerUrl(serverUrl || '') || !apiKey) {
    $('envoyer').disabled = false;
    return statut('Enregistre une adresse HTTPS et ta clé API dans l’extension.');
  }
  let ok = 0, erreurs = 0;
  // Déclenché explicitement par l'utilisateur, sans envoi automatique.
  for (const annonce of annoncesDetectees) {
    try {
      const response = await fetch(serverUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ titre: annonce.titre, marque: annonce.marque || 'Non précisée',
          prix: annonce.prix, taille: annonce.taille || 'Non précisée', etat: annonce.etat || 'Non précisé',
          lien: annonce.lien, image: annonce.image })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      ok++;
    } catch { erreurs++; }
  }
  statut(`${ok} annonce(s) envoyée(s), ${erreurs} erreur(s).`);
  annoncesDetectees = [];
});
