// Shared JS (dashboard polling lives in index.html).
// Clicking an occupied slot shows its vehicle info.
document.addEventListener('click', (e) => {
  const el = e.target.closest('.slot.Occupied');
  if (el && el.title) alert(el.title);
});
