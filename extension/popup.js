const serverUrlInput = document.getElementById("serverUrl");
const apiKeyInput = document.getElementById("apiKey");
const statut = document.getElementById("statut");
const resultats = document.getElementById("resultats");
const boutonEnvoyer = document.getElementById("envoyer");

let annoncesDetectees = [];

chrome.storage.local.get(
    ["serverUrl", "apiKey"],
    (config) => {
        if (config.serverUrl) serverUrlInput.value = config.serverUrl;
        if (config.apiKey) apiKeyInput.value = config.apiKey;
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

    await chrome.storage.local.set({ serverUrl, apiKey });
    statut.textContent = "Configuration enregistrée !";
});

// Scanner les annonces visibles
document.getElementById("scanner").addEventListener("click", async () => {
    statut.textContent = "Recherche des annonces...";
    resultats.replaceChildren();
    annoncesDetectees = [];
    boutonEnvoyer.disabled = true;

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

            annoncesDetectees = reponse?.annonces || [];
            statut.textContent = annoncesDetectees.length + " annonce(s) trouvée(s).";

            annoncesDetectees.forEach((annonce) => {
                const bloc = document.createElement("div");
                const titre = document.createElement("p");
                const prix = document.createElement("p");
                const lien = document.createElement("a");

                titre.textContent = annonce.titre || "Sans titre";
                prix.textContent = annonce.prix + " €";

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

            boutonEnvoyer.disabled = annoncesDetectees.length === 0;
        }
    );
});

// Envoyer manuellement les annonces à Discord
boutonEnvoyer.addEventListener("click", async () => {
    const config = await chrome.storage.local.get(["serverUrl", "apiKey"]);

    if (!config.serverUrl || !config.apiKey) {
        statut.textContent = "Enregistre d'abord ta configuration.";
        return;
    }

    if (annoncesDetectees.length === 0) {
        statut.textContent = "Aucune annonce à envoyer.";
        return;
    }

    boutonEnvoyer.disabled = true;
    let envoyees = 0;
    let erreurs = 0;

    const marques = [
        "the north face", "ralph lauren", "tommy hilfiger",
        "stone island", "new balance", "nike jordan",
        "hugo boss", "carhartt", "patagonia", "supreme",
        "stussy", "adidas", "lacoste", "burberry",
        "dior", "gucci", "prada", "levis", "dickies",
        "arcteryx", "asics", "salomon", "nike"
    ];

    for (const annonce of annoncesDetectees) {
        const titre = annonce.titre || "Annonce Vinted";
        const texte = titre.toLowerCase();
        const marque = marques.find(m => texte.includes(m)) || "Non précisée";

        try {
            const response = await fetch(config.serverUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${config.apiKey}`
                },
                body: JSON.stringify({
                    titre,
                    marque,
                    prix: Number(annonce.prix),
                    lien: annonce.lien,
                    image: annonce.image
                })
            });

            if (response.ok) {
                envoyees++;
            } else {
                erreurs++;
            }
        } catch (error) {
            erreurs++;
        }
    }

    statut.textContent =
        `${envoyees} annonce(s) envoyée(s), ${erreurs} erreur(s).`;

    // Évite de renvoyer accidentellement le même lot.
    annoncesDetectees = [];
});

