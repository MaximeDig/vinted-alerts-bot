(() => {
    function trouverAnnonces() {
        const liens = document.querySelectorAll('a[href*="/items/"]');
        const annonces = [];

        liens.forEach(lien => {
            const url = lien.href;

            if (!url.includes("vinted.fr/items/")) return;

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

        return annonces;
    }

    window.addEventListener("message", event => {
        if (event.data?.type === "VINTED_SCAN") {
            const annonces = trouverAnnonces();

            window.postMessage({
                type: "VINTED_SCAN_RESULT",
                annonces
            }, "*");
        }
    });
})();
