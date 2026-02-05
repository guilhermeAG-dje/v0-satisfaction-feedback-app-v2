function registar(grau) {
  const buttons = document.getElementById("buttons");
  const mensagem = document.getElementById("mensagem");
  const loading = document.getElementById("loading");
  const timer = document.getElementById("timer");

  if (!buttons || !mensagem || !loading || !timer) return;

  buttons.querySelectorAll("button").forEach(btn => {
    btn.disabled = true;
    btn.style.opacity = "0.6";
  });

  loading.style.display = "block";
  mensagem.style.display = "none";

  fetch("/submit_feedback", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grau=${encodeURIComponent(grau)}`
  })
    .then(r => {
      if (!r.ok) throw new Error("erro");
      return r.text();
    })
    .then(() => {
      loading.style.display = "none";
      mensagem.style.display = "block";

      let count = TIMEOUT_SEGUNDOS;
      timer.innerText = String(count);

      const interval = setInterval(() => {
        count -= 1;
        timer.innerText = String(count);
        if (count <= 0) {
          clearInterval(interval);
          mensagem.style.display = "none";
          buttons.querySelectorAll("button").forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = "1";
          });
        }
      }, 1000);
    })
    .catch(() => {
      loading.style.display = "none";
      buttons.querySelectorAll("button").forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = "1";
      });
      alert("Nao foi possivel registar. Tenta novamente.");
    });
}
