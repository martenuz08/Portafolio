document.addEventListener("DOMContentLoaded", function() {
  const boton = document.getElementById("btnReproducir");
  const audio = document.getElementById("audioAcerca");

  boton.addEventListener("click", () => {
    if (audio.paused) {
      audio.play();
      boton.textContent = "⏸️ Pausar Música";
      boton.classList.add("reproduciendo");
    } else {
      audio.pause();
      boton.textContent = "🎧 Reproducir Música";
      boton.classList.remove("reproduciendo");
    }
  });
});