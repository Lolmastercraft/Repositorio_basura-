export function toast(txt, isError = false){
    const box = document.getElementById('toast-box');
    if (!box) return alert(txt);          // fallback
    const div = document.createElement('div');
    div.className = 'toast' + (isError ? ' error' : '');
    div.textContent = txt;
    box.appendChild(div);
    /* remueve al terminar la animación fadeout */
    setTimeout(() => box.removeChild(div), 3400);
  }