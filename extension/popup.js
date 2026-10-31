
const serverUrlInput = document.getElementById("serverUrl");
const apiKeyInput = document.getElementById("apiKey");
const statut = document.getElementById("statut");
const resultats = document.getElementById("resultats");

// Charger la configuration enregistrée
chrome.storage.local.get(
    ["serverUrl", "apiKey"],
    (config) => {
        if (config.serverUrl) {
            serverUrlInput.value = config.serverUrl;
        }

        if (config.apiKey) {
            apiKeyInput.value = config.apiKey;
        }
    }
);

// Enregistrer la configuration
document.getElementById("sauvegarder").addEventListener("click", async () => {
    const serverUrl = serverUrlInput.value.trim().replace(/\/+$/, "");
    const apiKey = apiKeyInput.value.trim();

    if (!serverUrl.startsWith("https://") || !serverUrl.endsWith("/annonce")) {
        statut.textContent = "Vérifie l'adresse de réception.";
        return;
    }

    if (!apiKey) {
        statut.textContent = "Entre ta clé API.";
        return;
    }

    await chrome.storage.local.set({
        serverUrl,
        apiKey
    });

    statut.textContent = "Configuration enregistrée !";
});

// Scanner les annonces visibles
document.getElementById("scanner").addEventListener("click", async () => {
    statut.textContent = "Recherche des annonces...";
    resultats.replaceChildren();

    const [onglet] = await chrome.tabs.query({
        active: true,
        currentWindow: true
    });

    if (!onglet || !/^https:\/\/www\.vinted\.(fr|be|de|es|it|pt|lu)\//.test(onglet.url || "")) {
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

                if (annonce.image) {
                    const photo = document.createElement("img");
                    photo.src = annonce.image;
                    photo.alt = "Photo de l'annonce";
                    photo.width = 120;
                    bloc.appendChild(photo);
                }

                bloc.append(titre, prix, lien);
                resultats.appendChild(bloc);
            });
        }
    );
});

