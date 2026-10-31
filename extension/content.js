
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "VINTED_SCAN") return;

    const prixElements = document.querySelectorAll(
        '[data-testid^="product-item-id-"][data-testid$="--price-text"]'
    );

    const annonces = [];
    const dejaVues = new Set();

    prixElements.forEach((element) => {
        const testId = element.getAttribute("data-testid");
        const correspondance = testId.match(
            /^product-item-id-(\d+)--price-text$/
        );

        if (!correspondance) return;

        const id = correspondance[1];

        const prixTexte = element.textContent
            .replace(/\u00a0/g, " ")
            .trim();

        const matchPrix = prixTexte.match(
            /(\d+(?:[,.]\d{1,2})?)\s*€/
        );

        if (!matchPrix) return;

        const prix = Number(matchPrix[1].replace(",", "."));

        if (!Number.isFinite(prix)) return;

        const lien = document.querySelector(
            `a[href*="/items/${id}"]`
        );

        if (!lien || dejaVues.has(id)) return;

        dejaVues.add(id);

        const bloc = element.closest('[data-testid^="product-item-"]')
            || lien.parentElement;

        const image = bloc?.querySelector("img");

        annonces.push({
            titre: bloc?.innerText?.slice(0, 150) || "Sans titre",
            prix: prix,
            lien: lien.href,
            image: image?.src || null
        });
    });

    sendResponse({ annonces });
});

