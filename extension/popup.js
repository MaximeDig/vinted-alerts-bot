document.getElementById("scanner").addEventListener("click", async () => {
    const statut = document.getElementById("statut");
    const resultats = document.getElementById("resultats");

    statut.textContent = "Recherche des annonces...";
    resultats.replaceChildren();

    const [onglet] = await chrome.tabs.query({
        active: true,
        currentWindow: true
    });

    if (!onglet || !onglet.url?.includes("vinted.fr")) {
        statut.textContent = "Ouvre d'abord Vinted.";
        return;
    }

    chrome.tabs.sendMessage(
        onglet.id,
        { type: "VINTED_SCAN" },
        (reponse) => {
            if (chrome.runtime.lastError) {
                statut.textContent = "Recharge la page Vinted.";
                return;
            }

            const annonces = reponse?.annonces || [];
            statut.textContent = annonces.length + " annonce(s) trouvée(s).";

            annonces.forEach((annonce) => {
                const bloc = document.createElement("div");
                const titre = document.createElement("p");
                const prix = document.createElement("p");
                const lien = document.createElement("a");

                titre.textContent = annonce.titre || "Sans titre";
                prix.textContent = annonce.prix || "Prix inconnu";

                lien.textContent = "Voir l'annonce";
                lien.href = annonce.lien;
                lien.target = "_blank";
                lien.rel = "noopener noreferrer";

                bloc.append(titre, prix, lien);
                resultats.appendChild(bloc);
            });
        }
    );
});
