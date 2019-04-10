/* hotkeys (TODO: make configurable) */

var spinCounter = 0;

function updateSpinner() {
    spinner = document.getElementById("spinner");
    if (spinCounter > 0) {
	spinner.style.display = 'inline';
    } else {
	spinner.style.display = 'none';
    }
}

function updatePicks() {
    var candidates = document.getElementsByClassName("pa-candidate");
    var accepted = METADATA['accepted'];
    var rejected = METADATA['rejected'];
    for (let i=0; i<candidates.length; i++) {
	let element = candidates[i];
	let cid = element.id.replace("candidate-", "");
	if (accepted.includes(cid)) {
	    element.classList.add("accepted");
	    element.classList.remove("rejected");
	} else if(rejected.includes(cid)) {
	    element.classList.add("rejected");
	    element.classList.remove("accepted");
	} else {
	    element.classList.remove("rejected");
	    element.classList.remove("accepted");
	}
    }
}

function spinUp() {
    spinCounter++;
    updateSpinner();
}

function spinDown() {
    spinCounter--;
    updateSpinner();
}

function isAbsolute(url) {
    var re = new RegExp('^[a-z]+://', 'i');
    return re.test(url);
}

function makeUrl(url, params) {
    // Adapted from https://fetch.spec.whatwg.org/#fetch-api
    if (isAbsolute(url)) {
	url = new URL(url);
    } else {
	url = new URL(url, window.location.origin);
    }
    Object.keys(params).forEach(
	key => url.searchParams.append(key, params[key])
    );
    return url;
}

async function pickCandidate(pick) {
    spinUp();
    var url = makeUrl(PICK_ANNO_URL, { "choice":  pick });
    var response = await fetch(url);
    var data = await response.json();
    METADATA['accepted'] = data['accepted'];
    METADATA['rejected'] = data['rejected'];
    updatePicks(data.picked);
    spinDown();
    return data;
}

/* set up events */

document.addEventListener('keydown', function(event) {
    // HOTKEYS defined in config.py
    if (event.key in HOTKEYS) {
	let pick = HOTKEYS[event.key];
	pickCandidate(pick);
    }
});

function load() {
    var candidates = document.getElementsByClassName("pa-candidate");
    for (let i=0; i<candidates.length; i++) {
	let element = candidates[i];
	let cid = element.id.replace("candidate-", "");
	element.onclick = function() {
	    pickCandidate(cid);
	};
    }
    updatePicks();
}
