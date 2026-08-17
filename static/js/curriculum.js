(()=>{'use strict';
  const counters=[...document.querySelectorAll('[data-counter]')];
  const animateCounter=el=>{if(el.dataset.done)return;el.dataset.done='1';const target=Number(el.dataset.counter)||0,start=performance.now(),duration=900;const tick=now=>{const p=Math.min((now-start)/duration,1);el.textContent=Math.round(target*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)};
  if('IntersectionObserver'in window){const io=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){animateCounter(entry.target);io.unobserve(entry.target)}}),{threshold:.45});counters.forEach(el=>io.observe(el))}else counters.forEach(animateCounter);
  document.querySelectorAll('.module-card').forEach(card=>card.addEventListener('toggle',()=>{if(card.open)document.querySelectorAll('.module-card[open]').forEach(other=>{if(other!==card)other.open=false})}));
  document.querySelector('.start-fit')?.addEventListener('click',()=>document.querySelector('.quick-fit')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'}));
})();
