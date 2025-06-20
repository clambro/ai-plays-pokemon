const ALL_BADGES = [
    "BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE", "RAINBOWBADGE",
    "SOULBADGE", "MARSHBADGE", "VOLCANOBADGE", "EARTHBADGE"
];

function updateDisplay(data) {
    // --- Info Bar ---
    document.getElementById('money').textContent = `¥${data.money.toLocaleString()}`;
    document.getElementById('iteration').textContent = data.iteration;
    document.getElementById('caught-seen').textContent = `${data.pokedex_caught}/${data.pokedex_seen}`;
    document.getElementById('total-cost').textContent = `$${data.total_cost.toFixed(2)}`;

    const hours = Math.floor(data.play_time_seconds / 3600);
    const minutes = Math.floor((data.play_time_seconds % 3600) / 60);
    document.getElementById('play-time').textContent = `${hours}h ${minutes}m`;


    // --- Badges ---
    const badgesContainer = document.getElementById('badges-container');
    badgesContainer.innerHTML = ''; // Clear old badges
    ALL_BADGES.forEach(badgeName => {
        const badgeImg = document.createElement('img');
        badgeImg.src = `assets/badges/${badgeName.toLowerCase()}.png`;
        badgeImg.title = badgeName;
        badgeImg.className = 'badge-icon';
        if (data.badges.includes(badgeName)) {
            badgeImg.classList.add('earned');
        }
        badgesContainer.appendChild(badgeImg);
    });


    // --- Goals ---
    const goalsDiv = document.getElementById('goals');
    goalsDiv.innerHTML = ''; // Clear old goals
    if (data.goals && data.goals.length > 0) {
        data.goals.forEach((goal) => {
            const goalEl = document.createElement('li');
            goalEl.className = 'goal';
            goalEl.textContent = goal;
            goalsDiv.appendChild(goalEl);
        });
    } else {
        goalsDiv.innerHTML = '<li class="no-data">Awaiting objectives...</li>';
    }

    // --- Log ---
    const logDiv = document.getElementById('log-content');
    logDiv.innerHTML = '';
    if (data.log && data.log.length > 0) {
        data.log.forEach(entry => {
            const p = document.createElement('p');
            p.textContent = `[${entry.iteration}] ${entry.thought}`;
            logDiv.appendChild(p);
        });
    }


    // --- Party ---
    const partyDiv = document.getElementById('party');
    partyDiv.innerHTML = ''; // Clear old party

    // Always show 6 cards, add empty placeholders if needed
    const pokemonToShow = data.party || [];
    for (let i = 0; i < 6; i++) {
        if (i < pokemonToShow.length) {
            const card = createPokemonCard(pokemonToShow[i]);
            partyDiv.appendChild(card);
        } else {
            // Add empty placeholder card
            const emptyCard = document.createElement('div');
            emptyCard.className = 'pokemon-card empty';
            partyDiv.appendChild(emptyCard);
        }
    }
}

function createPokemonCard(pokemon) {
    const template = document.getElementById('pokemon-card-template');
    const card = template.content.cloneNode(true).querySelector('.pokemon-card');

    // Calculate HP percentage and color
    const hpPercent = (pokemon.hp / pokemon.max_hp) * 100;
    let hpColor;
    if (hpPercent > 50) hpColor = '#33ff33';
    else if (hpPercent > 20) hpColor = '#fde64b';
    else hpColor = '#ff3333';

    // Add fainted class if needed
    if (pokemon.hp === 0) {
        card.classList.add('fainted');
    }

    // Set sprite
    const clean_name = pokemon.species.toLowerCase().replace(" ", "").replace("♀", "f").replace("♂", "m").replace("'", "");
    const sprite = card.querySelector('.pokemon-sprite');
    sprite.src = `assets/pokemon/${clean_name}.png`;
    sprite.alt = pokemon.species;

    // Set name and status
    const nameEl = card.querySelector('.pokemon-name');
    nameEl.textContent = pokemon.name;
    nameEl.title = pokemon.name;

    const statusEl = card.querySelector('.status');
    statusEl.textContent = pokemon.hp > 0 && pokemon.status ? pokemon.status : '';

    // Set species and level
    const speciesEl = card.querySelector('.pokemon-species');
    speciesEl.textContent = `${pokemon.species} - Lv.${pokemon.level}`;

    // Set type badges
    const typeContainer = card.querySelector('.type-badge-container');
    typeContainer.innerHTML = '';
    if (pokemon.type1) {
        const type1Badge = document.createElement('span');
        type1Badge.className = `type-badge type-${pokemon.type1.toLowerCase()}`;
        type1Badge.textContent = pokemon.type1;
        typeContainer.appendChild(type1Badge);
    }
    if (pokemon.type2) {
        const type2Badge = document.createElement('span');
        type2Badge.className = `type-badge type-${pokemon.type2.toLowerCase()}`;
        type2Badge.textContent = pokemon.type2;
        typeContainer.appendChild(type2Badge);
    }

    // Set HP bar
    const hpFill = card.querySelector('.hp-fill');
    hpFill.style.width = `${hpPercent}%`;
    hpFill.style.backgroundColor = hpColor;

    // Set HP text
    const hpText = card.querySelector('.hp-text');
    hpText.textContent = `${pokemon.hp} / ${pokemon.max_hp}`;

    // Set moves
    const movesList = card.querySelector('.moves-list');
    movesList.innerHTML = '';
    pokemon.moves.forEach(move => {
        const moveLi = document.createElement('li');
        moveLi.textContent = move;
        movesList.appendChild(moveLi);
    });

    return card;
}

async function fetchData() {
    try {
        const response = await fetch('/api/state.json');
        const data = await response.json();
        updateDisplay(data);

    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Initial load and periodic refresh
fetchData();
setInterval(fetchData, 1000);