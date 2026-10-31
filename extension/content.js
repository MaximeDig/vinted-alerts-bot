chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "VINTED_SCAN") return;
  const annonces = [], ids = new Set();
  const liens = [...document.querySelectorAll('a[href*="/items/"]')];
  const elements = document.querySelectorAll('[data-testid^="product-item-id-"][data-testid$="--price-text"]');

  function photoUrl(img) {
    if (!img) return null;
    const candidats = [img.currentSrc, img.getAttribute("src"), img.getAttribute("data-src")];
    const srcset = img.getAttribute("srcset") || img.getAttribute("data-srcset");
    if (srcset) candidats.push(...srcset.split(",").map(s => s.trim().split(/\s+/)[0]));
    for (const src of candidats) {
      if (!src || /^(data:|blob:)/.test(src)) continue;
      try {
        const url = new URL(src, location.href);
        if (url.protocol === "https:") return url.href;
      } catch (_) {}
    }
    return null;
  }

  for (const element of elements) {
    const id = element.getAttribute("data-testid")?.match(/^product-item-id-(\d+)--price-text$/)?.[1];
    if (!id || ids.has(id)) continue;
    const prixTexte = (element.textContent || "").replace(/\u00a0/g, " ");
    const matchPrix = prixTexte.match(/(\d+(?:[.,]\d{1,2})?)\s*€/);
    if (!matchPrix) continue;
    const prix = Number(matchPrix[1].replace(",", "."));
    if (!Number.isFinite(prix)) continue;
    const lien = liens.find(a => {
      try { return new URL(a.href).pathname.match(/^\/items\/(\d+)(?:-|\/|$)/)?.[1] === id; }
      catch (_) { return false; }
    });
    if (!lien) continue;

    let carte = lien;
    for (let n = 0; n < 7 && carte.parentElement; n++) {
      if (carte.querySelector("img") && carte.contains(element)) break;
      carte = carte.parentElement;
    }
    const img = carte.querySelector("img") || lien.querySelector("img");
    const titre = [lien.getAttribute("title"), lien.getAttribute("aria-label"),
      img?.getAttribute("alt")].find(s => s?.trim())?.trim() || "Annonce Vinted";
    const texte = (carte.innerText || "").replace(/\s+/g, " ");
    const taille = texte.match(/\b(?:XXXL|XXL|XL|XS|XXS|S|M|L|\d{2,3}(?:\s*\/\s*\d{2,3})?)\b/)?.[0] || "Non précisée";
    const etat = ["Neuf avec étiquette", "Neuf sans étiquette", "Très bon état",
      "Bon état", "Satisfaisant"].find(s => texte.toLowerCase().includes(s.toLowerCase())) || "Non précisé";
    ids.add(id);
    annonces.push({ titre, prix, lien: lien.href, image: photoUrl(img), taille, etat });
  }
  sendResponse({ annonces });
});
