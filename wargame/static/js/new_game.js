const ensurePlayerOnOnlyOneTeam = () => {
  const getPickersForTeam = team => {
    return document.querySelectorAll(`#create-${team}-team .entity-player-picker select`);
  };

  const pickers = {
    red: getPickersForTeam('red'),
    blue: getPickersForTeam('blue'),
  }

  const hideOtherTeamOptions = (thisTeam, otherTeam) => {
    pickers[thisTeam].forEach(p => p.addEventListener('change', () => {
      const playersInTeam = Array.from(pickers[thisTeam]).map(p => p.value);
      pickers[otherTeam].forEach(p => {
        for (option of p.children) {
          if (playersInTeam.includes(option.value)) {
            option.classList.add('hidden-option');
          } else {
            option.classList.remove('hidden-option');
          }
        }
      });
    }));
  };

  hideOtherTeamOptions('red', 'blue');
  hideOtherTeamOptions('blue', 'red');
};

window.onload = () => {
  ensurePlayerOnOnlyOneTeam();
};
