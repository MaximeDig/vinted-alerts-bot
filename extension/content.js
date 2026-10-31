
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "VINTED_SCAN") return;

    const liens = document.querySelectorAll('a[href*="/items/"]');
    const annonces = [];
    const dejaVues = new Set();

    liens.forEach((lien) => {
        const url = lien.href;

        if (!/^https:\/\/www\.vinted\.(fr|be|de|es|it|pt|lu)\/items\//.test(url)) {
            return;
        }

        if (dejaVues.has(url)) return;
        dejaVues.add(url);

        // Récupérer l'identifiant de l'annonce
        const correspondanceId = url.match(/\/items\/(\d+)/);
        if (!correspondanceId) return;

        const id = correspondanceId[1];

        // Trouver le prix correspondant exactement à cette annonce
        const prixElement = document.querySelector(
            `[data-testid="product-item-id-${id}--price-text"]`
        );

        const textePrix = prixElement?.textContent
            ?.replace(/\u00a0/g, " ")
            .trim();

        const correspondancePrix = textePrix?.match(
            /(\d+(?:[,.]\d{1,2})?)\s*€/
        );

        const prix = correspondancePrix
            ? Number(correspondancePrix[1].replace(",", "."))
            : null;

        // Récupérer l'image
        const bloc = lien.closest("div");
        const image = bloc?.querySelector("img");

        annonces.push({
            titre: bloc?.innerText?.slice(0, 150) || "Sans titre",
            prix: Number.isFinite(prix) ? prix : null,
            lien: url,
            image: image?.src || null
        });
    });

    sendResponse({ annonces });
});

