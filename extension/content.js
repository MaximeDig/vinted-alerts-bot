chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "VINTED_SCAN") return;

    const prixElements = document.querySelectorAll(
        '[data-testid^="product-item-id-"][data-testid$="--price-text"]'
    );

    const annonces = [];
    const dejaVues = new Set();

    prixElements.forEach((element) => {
        const testId = element.getAttribute("data-testid");
        const matchId = testId?.match(
            /^product-item-id-(\d+)--price-text$/
        );

        if (!matchId) return;

        const id = matchId[1];
        if (dejaVues.has(id)) return;

        const prixTexte = (element.innerText || element.textContent || "")
            .replace(/\u00a0/g, " ")
            .trim();

        const matchPrix = prixTexte.match(
            /(\d+(?:[,.]\d{1,2})?)\s*€/
        );

        if (!matchPrix) return;

        const prix = Number(matchPrix[1].replace(",", "."));

        if (!Number.isFinite(prix)) return;

        const liens = [...document.querySelectorAll('a[href*="/items/"]')];

        const lien = liens.find(a =>
            new RegExp(`/items/${id}(?:-|\\?|$)`).test(a.href)
        );

        if (!lien) return;

        dejaVues.add(id);

        // Chercher la photo autour du lien de l'annonce
        const carte =
            lien.closest('[data-testid^="product-item-"]') ||
            lien.closest("article") ||
            lien.parentElement?.parentElement ||
            lien;

        const image =
            lien.querySelector("img") ||
            carte.querySelector("img");

        const titre =
            image?.alt ||
            lien.getAttribute("aria-label") ||
            carte.innerText?.slice(0, 150) ||
            "Annonce Vinted";

        const urlImage =
            image?.currentSrc ||
            image?.src ||
            image?.getAttribute("src") ||
            null;

        annonces.push({
            titre,
            prix,
            lien: lien.href,
            image: urlImage
        });
    });

    sendResponse({ annonces });
});
