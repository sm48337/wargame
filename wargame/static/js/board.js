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

const timerManagement = () => {
  const display = document.getElementById('round-timer');
  const form = document.getElementById('board');
  const refreshTime = () => {
    const now = new Date();
    const utc = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
    const timeLeft = new Date(window.roundEnd - utc);
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
    if (!display) return;
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
  setInterval(refreshTime, 1000);
  refreshTime();
}

const refreshIfTurnOver = () => {
  fetch(window.turnStartUrl)
    .then(resp => resp.json())
    .then(data => {
      const turn_start = new Date(data.start);
      const current_time = new Date();
      if (data.turn != window.turn || turn_start > current_time) {
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

window.onload = () => {
  addClassToTargetOnHover('.attack', 'attack-target');
  addClassToTargetOnHover('.transfer', 'transfer-target');
  makeOnlySelectedOptionVisible();
  displayRevitalizeCost();
  changeMaxTransferValue();
  if (!window.victor) {
    timerManagement();
    if (!window.waitingForMove) {
      setInterval(refreshIfTurnOver, 5000);
    }
  }
  handleAssetsDialog();
  handleBlackMarket();
};