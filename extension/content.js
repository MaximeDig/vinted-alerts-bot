

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "VINTED_SCAN") return;

    const prixElements = document.querySelectorAll(
        '[data-testid^="product-item-id-"][data-testid$="--price-text"]'
    );

    const annonces = [];
    const dejaVues = new Set();

    prixElements.forEach((element) => {
        const testId = element.getAttribute("data-testid");
        const matchId = testId.match(
            /^product-item-id-(\d+)--price-text$/
        );

        if (!matchId) return;

        const id = matchId[1];
        if (dejaVues.has(id)) return;

const prixTexte = (element.innerText || element.textContent || "")
    .replace(/\u00a0/g, " ")
    .trim();

console.log("TEST PRIX :", id, prixTexte);

        const matchPrix = prixTexte.match(
            /(\d+(?:[,.]\d{1,2})?)\s*€/
        );

        if (!matchPrix) return;

        const prix = Number(matchPrix[1].replace(",", "."));

        if (!Number.isFinite(prix)) return;

        const lien = [...document.querySelectorAll('a[href*="/items/"]')]
            .find(a => a.href.includes(`/items/${id}-`));

        if (!lien) return;

        dejaVues.add(id);

        const bloc = element.closest('[data-testid^="product-item-"]')
            || element.parentElement;

        const image = bloc?.querySelector("img");

        annonces.push({
            titre: bloc?.innerText?.slice(0, 150) || "Annonce Vinted",
            prix,
            lien: lien.href,
            image: image?.src || null
        });
    });

    sendResponse({ annonces });
});


