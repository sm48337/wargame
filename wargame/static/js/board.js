const setTitle = () => document.title = `Wargame: ${window.currentUser} - ${window.playerTeam}`;

const scrollDown = () => window.scroll(0, 100);

const resizeBackground = () => {
  const board = document.getElementById('board');
  const background = document.getElementById('background-image');

  const boardRect = board.getBoundingClientRect();
  background.height = boardRect.height;
  background.width = boardRect.width;
};

const addClassToTargetOnHover = (selector, className) => {
  const selected = document.querySelectorAll(selector);
  selected.forEach(source => {
    const target = document.getElementById(source.attributes.target.value);
    source.addEventListener('mouseenter', () => {
      target.classList.add(className);
    });
    source.addEventListener('mouseleave', () => {
      target.classList.remove(className);
    });
  });
};

const makeOnlySelectedOptionVisible = () => {
  const actionRadios = document.querySelectorAll('.entity-actions input[type="radio"]');
  actionRadios.forEach(radio => {
    const controlledInputs = document.querySelectorAll('.' + radio.id);
    const entityId = radio.parentNode.parentNode.parentNode.parentNode.id;
    const allHiddenInputs = Array.from(document.querySelectorAll(`#${entityId} .action-hide`));

    radio.addEventListener('change', () => {
      allHiddenInputs.forEach(input => input.classList.add('action-hide'));
      if (controlledInputs) controlledInputs.forEach(input => input.classList.remove('action-hide'));
    });
  });
};

const displayRevitalizeCost = () => {
  const costMapping = window.vitality_recovery_cost;
  const revitalizeInputs = document.querySelectorAll('.revitalize-amount');
  revitalizeInputs.forEach(input => input.addEventListener('change', e => {
    const amount = e.target.valueAsNumber;
    input.previousElementSibling.textContent = costMapping[amount];
  }));
};

const changeMaxTransferValue = () => {
  const inputsByEntity = {};
  const transferInputs = document.querySelectorAll('[class*=__transfer-input]');
  transferInputs.forEach(input => {
    const entityId = input.className.split('__')[0];
    if (inputsByEntity[entityId]) {
      inputsByEntity[entityId].push(input);
    } else {
      inputsByEntity[entityId] = [input];
    }
  });
  Object.values(inputsByEntity).forEach(entityInputs => {
    entityInputs.forEach(input => {
      input.addEventListener('change', e => {
        const amountChanged = e.target.value - e.target.dataset.value;
        e.target.dataset.value = e.target.value;
        entityInputs.filter(i => i !== input).forEach(otherInput => {
          otherInput.max -= amountChanged;
        });
      });
    });
  });
};

const refreshTime = () => {
  if (!window.refreshTimeTimer) {
    window.refreshTimeTimer = setInterval(refreshTime, 1000);
  }
  if (window.isPaused) {
    return;
  }
  const display = document.getElementById('round-timer');
  const form = document.getElementById('board');

  const timeLeft = new Date(window.secondsLeft * 1000);
  window.secondsLeft -= 1;
  const options = {
    minute: '2-digit',
    second: '2-digit'
  };
  if (window.waitingForMove) {
    if (timeLeft.getTime() <= 0) {
      form.submit();
    }
  } else if (timeLeft.getTime() <= -5000) {
    location.reload();
  }

  display.textContent = timeLeft.toLocaleTimeString('en-us', options);
  if (timeLeft.getTime() < 1 * 60 * 1000) {
    display.classList.remove('time-green');
    display.classList.remove('time-yellow');
    display.classList.add('time-red');
  } else if (timeLeft.getTime() < 2 * 60 * 1000) {
    display.classList.remove('time-green');
    display.classList.add('time-yellow');
  }
};

const timerManagement = () => {
  refreshTime();
  setInterval(refreshIfTurnOver, 5000);
  refreshIfTurnOver();
}

const refreshIfTurnOver = () => {
  const display = document.getElementById('round-timer');

  fetch(window.timeLeftUrl)
    .then(resp => resp.json())
    .then(data => {
      window.secondsLeft = data.secondsLeft;
      window.isStarting = data.isStarting;
      window.startingDelay = data.startingDelay;

      if (window.isPaused !== data.isPaused) {
        window.isPaused = data.isPaused;
        if (window.isPaused) {
          clearInterval(window.refreshTimeTimer);
          delete window.refreshTimeTimer;
        }
        if (window.isStarting) {
          display.textContent = 'Starting...';
          setTimeout(refreshTime, window.startingDelay * 1000);
        }

        if (window.isPaused) {
          display.textContent = 'Paused';
        }
      }

      if (data.turn != window.turn) {
        location.reload();
      }
    });
};

const handleAssetsDialog = () => {
  const showButton = document.getElementById('open-assets');
  const assetsDialog = document.getElementById('assets');
  const closeDialog = document.getElementById('close-assets');
  const useButtons = document.querySelectorAll('.use-asset-btn');
  const activatedAssets = document.getElementById('activated-assets');

  if (!showButton) return;
  showButton.addEventListener('click', () => assetsDialog.showModal());
  closeDialog.addEventListener('click', e => {
    assetsDialog.close();
    e.preventDefault();
  });
  useButtons.forEach(btn => btn.addEventListener('click', () => {
    const assetIndex = btn.dataset.id;
    btn.parentNode.classList.add('activated-asset');
    if (activatedAssets.value) {
      activatedAssets.value += ', '
    }
    activatedAssets.value += assetIndex;
    btn.disabled = true;
  }));
};

const handleBlackMarket = () => {
  const scsOpen = document.getElementById('scs__black_market');
  const gchqOpen = document.getElementById('gchq__black_market');
  const marketDialog = document.getElementById('black-market');
  const cancelDialog = document.getElementById('cancel-bm');
  const confirmDialog = document.getElementById('confirm-bm');

  if (!cancelDialog) return;
  const openFunction = () => {
    marketDialog.showModal();
  };
  if (scsOpen) scsOpen.addEventListener('change', openFunction);
  if (gchqOpen) gchqOpen.addEventListener('change', openFunction);
  cancelDialog.addEventListener('click', e => {
    marketDialog.close();
    e.preventDefault();
  });
  confirmDialog.addEventListener('click', e => {
    marketDialog.close();
    scsOpen.parentNode.parentNode.parentNode.classList.remove('active');
    gchqOpen.parentNode.parentNode.parentNode.classList.remove('active');
    e.preventDefault();
  });
};

const positionArrows = () => {
  const arrows = document.querySelectorAll('svg.arrow');
  arrows.forEach(arrow => {
    const source = document.getElementById(arrow.dataset.from);
    const target = document.getElementById(arrow.dataset.to);
    const line = arrow.children[1];

    const sourceRect = source.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    // Source completely to the left of the target -> line between the source's right side and the target's left side
    if (sourceRect.x + sourceRect.width < targetRect.x) {
      line.x1.baseVal.value = sourceRect.x + sourceRect.width;
      line.x2.baseVal.value = targetRect.x;
    // Source completely to the right of the target -> line between the source's left side and the target's right side
    } else if (targetRect.x + targetRect.width < sourceRect.x) {
      line.x1.baseVal.value = sourceRect.x;
      line.x2.baseVal.value = targetRect.x + targetRect.width;
    // Source and target overlap on the X axis -> line between middle points of both
    } else {
      line.x1.baseVal.value = sourceRect.x + sourceRect.width / 2;
      line.x2.baseVal.value = targetRect.x + targetRect.width / 2;
    }
    // Source completely over the target -> line between the source's bottom and the target's top
    if (sourceRect.y + sourceRect.height < targetRect.y) {
      line.y1.baseVal.value = sourceRect.y + sourceRect.height;
      line.y2.baseVal.value = targetRect.y;
    // Source completely under the target -> line between the source's top and the target's bottom
    } else if (targetRect.y + targetRect.height < sourceRect.y) {
      line.y1.baseVal.value = sourceRect.y;
      line.y2.baseVal.value = targetRect.y + targetRect.height;
    // Source and target overlap on the Y axis -> line between middle points of both
    } else {
      line.y1.baseVal.value = sourceRect.y + sourceRect.height / 2;
      line.y2.baseVal.value = targetRect.y + targetRect.height / 2;
    }
    line.y1.baseVal.value += window.scrollY;
    line.y2.baseVal.value += window.scrollY;
  });
};

const handlePauseButton = () => {
  const pauseButton = document.getElementById('toggle-pause-button');
  pauseButton.hidden = false;
  pauseButton.addEventListener('click', e => {
    e.preventDefault()
    fetch(window.togglePauseUrl)
      .then(resp => resp.json())
      .then(data => {
        pauseButton.textContent = data.paused ? '▶' : '⏸ ';
      });
  });
};

window.onload = () => {
  setTitle();
  scrollDown();
  addClassToTargetOnHover('.attack', 'attack-target');
  addClassToTargetOnHover('.transfer', 'transfer-target');
  makeOnlySelectedOptionVisible();
  displayRevitalizeCost();
  changeMaxTransferValue();
  if (!window.victor) {
    timerManagement();
    if (window.isOwner) {
      handlePauseButton();
    }
  }
  handleAssetsDialog();
  handleBlackMarket();
  positionArrows();
};

window.onresize = () => {
  positionArrows();
  resizeBackground();
};
