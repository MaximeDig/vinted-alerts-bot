chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "VINTED_SCAN") {
        const liens = document.querySelectorAll('a[href*="/items/"]');
        const annonces = [];
        const dejaVues = new Set();

        liens.forEach(lien => {
            const url = lien.href;

            if (!/^https:\/\/www\.vinted\.(fr|be|de|es|it|pt|lu)\/items\//.test(url)) return;
            if (dejaVues.has(url)) return;

            dejaVues.add(url);

            const bloc = lien.closest("div");
            if (!bloc) return;

            const texte = bloc.innerText || "";
            const prix = texte.match(/\d+(?:[,.]\d{1,2})?\s*€/);
            const image = bloc.querySelector("img");

            annonces.push({
                titre: texte.slice(0, 150),
                prix: prix ? prix[0] : "Non trouvé",
                lien: url,
                image: image ? image.src : null
            });
        });

        sendResponse({ annonces });
    }

    return true;
});
