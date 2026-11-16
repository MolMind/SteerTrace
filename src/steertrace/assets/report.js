(() => {
  'use strict';
  const cards = [...document.querySelectorAll('.event')];
  const search = document.getElementById('search');
  const buttons = [...document.querySelectorAll('[data-filter]')];
  let selected = 'all';
  function update() {
    const query = search.value.trim().toLocaleLowerCase();
    let count = 0;
    cards.forEach(card => {
      const categoryMatches = selected === 'all' || (selected === 'choice' ? card.dataset.choice === 'true' : card.dataset.category === selected);
      card.hidden = !(categoryMatches && card.textContent.toLocaleLowerCase().includes(query));
      if (!card.hidden) count++;
    });
    document.querySelectorAll('.timeline-day').forEach(heading => {
      let sibling = heading.nextElementSibling;
      let visible = false;
      while (sibling && !sibling.classList.contains('timeline-day')) {
        if (sibling.classList.contains('event') && !sibling.hidden) visible = true;
        sibling = sibling.nextElementSibling;
      }
      heading.hidden = !visible;
    });
    document.getElementById('match-count').textContent = `显示 ${count} / ${cards.length} 个判断`;
    document.getElementById('no-matches').hidden = count !== 0 || cards.length === 0;
  }
  buttons.forEach(button => button.addEventListener('click', () => {
    selected = button.dataset.filter;
    buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    update();
  }));
  search.addEventListener('input', update);
  document.querySelectorAll('a[href^="#decision-"]').forEach(link => link.addEventListener('click', () => {
    search.value = '';
    selected = 'all';
    buttons.forEach(item => item.setAttribute('aria-pressed', String(item.dataset.filter === 'all')));
    update();
  }));
  const disclosures = [...document.querySelectorAll('details')];
  let printState;
  window.addEventListener('beforeprint', () => {
    printState = disclosures.map(item => item.open);
    disclosures.forEach(item => { item.open = true; });
  });
  window.addEventListener('afterprint', () => {
    disclosures.forEach((item, i) => { item.open = printState ? printState[i] : false; });
  });
  document.getElementById('print').addEventListener('click', () => window.print());
  document.getElementById('print').hidden = false;
  document.getElementById('filters').hidden = false;
  update();

  const guide = document.getElementById('guide');
  const steps = [...document.querySelectorAll('[data-guide]')];
  const panels = [...document.querySelectorAll('[data-guide-panel]')];
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const desktop = window.matchMedia('(min-width: 900px)');
  let active = -1;
  let frame = 0;
  function selectStep(index) {
    if (active === index) return;
    active = index;
    steps.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    panels.forEach((panel, i) => { panel.hidden = i !== index; });
    document.getElementById('guide-count').textContent = `0${index + 1} / 03`;
  }
  guide.classList.add('is-interactive');
  selectStep(0);
  const navLinks = [...document.querySelectorAll('nav a')];
  function scrollableTour() {
    return desktop.matches && !motion.matches && window.innerHeight > 780;
  }
  function onScroll() {
    frame = 0;
    const total = document.documentElement.scrollHeight - window.innerHeight;
    document.querySelector('.reading-progress span').style.transform =
      `scaleX(${total > 0 ? Math.min(1, Math.max(0, window.scrollY / total)) : 0})`;
    if (guide.classList.contains('is-scroll')) {
      const rect = guide.getBoundingClientRect();
      const distance = guide.offsetHeight - guide.querySelector('.guide-pin').offsetHeight - 190;
      const progress = Math.max(0, Math.min(1, (110 - rect.top) / Math.max(1, distance)));
      selectStep(Math.min(2, Math.floor(progress * 3)));
    }
    let current = null;
    navLinks.forEach(link => {
      const section = document.querySelector(link.getAttribute('href'));
      if (section.getBoundingClientRect().top <= 180) current = link;
    });
    navLinks.forEach(link => {
      if (link === current) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function requestUpdate() {
    if (!frame) frame = window.requestAnimationFrame(onScroll);
  }
  function layout() {
    guide.classList.toggle('is-scroll', scrollableTour());
    requestUpdate();
  }
  steps.forEach((button, i) => button.addEventListener('click', () => {
    selectStep(i);
    if (guide.classList.contains('is-scroll')) {
      const distance = guide.offsetHeight - guide.querySelector('.guide-pin').offsetHeight - 190;
      const y = window.scrollY + guide.getBoundingClientRect().top - 110 + distance * ((i + .15) / 3);
      window.scrollTo({top: y, behavior: 'instant'});
    }
  }));
  window.addEventListener('scroll', requestUpdate, {passive: true});
  window.addEventListener('resize', layout);
  motion.addEventListener('change', layout);
  layout();
})();
