document.getElementById("scanner").addEventListener("click", async () => {
    const statut = document.getElementById("statut");

    statut.textContent = "Recherche des annonces...";

    const [onglet] = await chrome.tabs.query({
        active: true,
        currentWindow: true
    });

    if (!onglet || !onglet.url.includes("vinted.fr")) {
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

            statut.textContent =
                annonces.length + " annonce(s) trouvée(s).";
        }
    );
});
