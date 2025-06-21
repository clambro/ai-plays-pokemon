import { z } from 'https://esm.sh/zod@3.22.4';

const ALL_BADGES = [
    "BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE", "RAINBOWBADGE",
    "SOULBADGE", "MARSHBADGE", "VOLCANOBADGE", "EARTHBADGE"
];

const statusMap = {
    'POISONED': { abbr: 'PSN', class: 'psn' },
    'BURNED': { abbr: 'BRN', class: 'brn' },
    'PARALYZED': { abbr: 'PAR', class: 'par' },
    'ASLEEP': { abbr: 'SLP', class: 'slp' },
    'FROZEN': { abbr: 'FRZ', class: 'frz' },
};

const PokemonSchema = z.object({
    name: z.string(),
    species: z.string(),
    type1: z.string(),
    type2: z.string().nullable(),
    level: z.number().int().positive(),
    hp: z.number().int().min(0),
    max_hp: z.number().int().positive(),
    status: z.string().nullable(),
    moves: z.array(z.string())
});

const LogEntrySchema = z.object({
    iteration: z.number().int().positive(),
    thought: z.string()
});

const GameStateSchema = z.object({
    iteration: z.number().int().positive(),
    money: z.number().int().min(0),
    pokedex_seen: z.number().int().min(0),
    pokedex_caught: z.number().int().min(0),
    total_cost: z.number().min(0),
    play_time_seconds: z.number().int().min(0),
    badges: z.array(z.string()),
    party: z.array(PokemonSchema),
    goals: z.array(z.string()),
    log: z.array(LogEntrySchema)
});

// Cache DOM references
const refs = {
    money: document.getElementById('money'),
    iteration: document.getElementById('iteration'),
    caughtSeen: document.getElementById('caught-seen'),
    totalCost: document.getElementById('total-cost'),
    playTime: document.getElementById('play-time'),
    badgesContainer: document.getElementById('badges-container'),
    goalsDiv: document.getElementById('goals'),
    logDiv: document.getElementById('log-content'),
    partyDiv: document.getElementById('party'),
    template: document.getElementById('pokemon-card-template'),
};

/**
 * @param {z.infer<typeof GameStateSchema>} data
 */
function updateDisplay(data) {
    const {
        money,
        iteration,
        pokedex_seen,
        pokedex_caught,
        total_cost,
        play_time_seconds,
        badges,
        goals,
        log,
        party
    } = data;

    if (
        !refs.money
        || !refs.iteration
        || !refs.caughtSeen
        || !refs.totalCost
        || !refs.playTime
        || !refs.badgesContainer
        || !refs.goalsDiv
        || !refs.logDiv
        || !refs.partyDiv
        || !refs.template
    ) {
        throw new Error('One or more elements not found');
    }

    // --- Info Bar ---
    refs.money.textContent = `¥${money.toLocaleString()}`;
    refs.iteration.textContent = iteration.toString();
    refs.caughtSeen.textContent = `${pokedex_caught}/${pokedex_seen}`;
    refs.totalCost.textContent = `$${total_cost.toFixed(2)}`;
    const hours = Math.floor(play_time_seconds / 3600);
    const minutes = Math.floor((play_time_seconds % 3600) / 60);
    refs.playTime.textContent = `${hours}h ${minutes}m`;

    // --- Badges ---
    const badgesFrag = document.createDocumentFragment();
    ALL_BADGES.forEach(name => {
        const img = document.createElement('img');
        img.className = 'badge-icon';
        img.src = `/assets/badges/${name.toLowerCase()}.png`;
        img.alt = name;
        if (badges.includes(name)) {
            img.classList.add('earned');
        }
        badgesFrag.appendChild(img);
    });
    refs.badgesContainer.replaceChildren(badgesFrag);

    // --- Goals ---
    const goalsFrag = document.createDocumentFragment();
    if (goals && goals.length) {
        goals.forEach(text => {
            const li = document.createElement('li');
            li.className = 'goal';
            li.textContent = text;
            goalsFrag.appendChild(li);
        });
    }
    refs.goalsDiv.replaceChildren(goalsFrag);
    refs.goalsDiv.scrollTop = refs.goalsDiv.scrollHeight;  // Auto-scroll to the bottom.

    // --- Log ---
    const logFrag = document.createDocumentFragment();
    if (log && log.length) {
        log.forEach((entry) => {
            const p = document.createElement('p');
            p.textContent = `[${entry.iteration}] ${entry.thought}`;
            logFrag.appendChild(p);
        });
    }
    refs.logDiv.replaceChildren(logFrag);
    refs.logDiv.scrollTop = refs.logDiv.scrollHeight;  // Auto-scroll to the bottom.

    // --- Party ---
    const partyFrag = document.createDocumentFragment();
    for (let i = 0; i < 6; i++) {
        if (party && i < party.length) {
            partyFrag.appendChild(createPokemonCard(party[i]));
        } else {
            const emptyCard = document.createElement('div');
            emptyCard.className = 'pokemon-card empty';
            partyFrag.appendChild(emptyCard);
        }
    }
    refs.partyDiv.replaceChildren(partyFrag);
}

/**
 * @param {z.infer<typeof PokemonSchema>} pokemon
 * @returns {HTMLElement}
 */
function createPokemonCard(pokemon) {
    if (!refs.template) {
        throw new Error('Template element not found');
    }
    const template = refs.template;
    const cardFrag = template.content.cloneNode(true);
    const card = cardFrag.querySelector('.pokemon-card');

    const hpPercent = (pokemon.hp / pokemon.max_hp) * 100;
    let hpColor;
    if (hpPercent > 50) hpColor = '#33ff33';
    else if (hpPercent > 20) hpColor = '#fde64b';
    else hpColor = '#ff3333';

    if (pokemon.hp === 0) card.classList.add('fainted');

    const sprite = card.querySelector('.pokemon-sprite');
    const clean_name = pokemon.species
        .toLowerCase()
        .replace(" ", "")
        .replace("♀", "f")
        .replace("♂", "m")
        .replace("'", "");
    sprite.src = `/assets/pokemon/${clean_name}.png`;
    sprite.alt = pokemon.species;

    const nameEl = card.querySelector('.pokemon-name');
    nameEl.textContent = pokemon.name;
    nameEl.title = pokemon.name;

    const statusEl = card.querySelector('.status');
    statusEl.className = 'status';
    if (pokemon.hp > 0 && pokemon.status) {
        const info = statusMap[pokemon.status.toUpperCase()];
        if (info) {
            statusEl.textContent = info.abbr;
            statusEl.classList.add(info.class);
        }
    }

    // Set species and level.
    const speciesEl = card.querySelector('.pokemon-species');
    speciesEl.textContent = `${pokemon.species} - Lv.${pokemon.level}`;

    // Set type badges.
    const typeContainer = card.querySelector('.type-badge-container');
    const typeFrag = document.createDocumentFragment();
    const t1 = document.createElement('span');
    t1.className = `type-badge type-${pokemon.type1.toLowerCase()}`;
    t1.textContent = pokemon.type1;
    typeFrag.appendChild(t1);
    if (pokemon.type2) {
        const t2 = document.createElement('span');
        t2.className = `type-badge type-${pokemon.type2.toLowerCase()}`;
        t2.textContent = pokemon.type2;
        typeFrag.appendChild(t2);
    }
    typeContainer.replaceChildren(typeFrag);

    // Set HP bar.
    const hpFill = card.querySelector('.hp-fill');
    hpFill.style.width = `${hpPercent}%`;
    hpFill.style.backgroundColor = hpColor;

    const hpText = card.querySelector('.hp-text');
    hpText.textContent = `${pokemon.hp} / ${pokemon.max_hp}`;

    // Set moves list.
    const movesList = card.querySelector('.moves-list');
    const movesFrag = document.createDocumentFragment();
    for (let i = 0; i < 4; i++) {
        const li = document.createElement('li');
        li.textContent = pokemon.moves[i] || '---';
        movesFrag.appendChild(li);
    }
    movesList.replaceChildren(movesFrag);

    return card;
}

async function fetchData() {
    try {
        const response = await fetch('/api/state.json');
        const raw = await response.json();
        if (!raw || Object.keys(raw).length === 0) return;

        const data = GameStateSchema.parse(raw);
        requestAnimationFrame(() => updateDisplay(data));
    } catch (err) {
        if (err instanceof z.ZodError) console.error('Validation errors:', err.errors);
        else console.error('Fetch error:', err);
    }
}

// Initial load and polling.
fetchData();
setInterval(fetchData, 100);