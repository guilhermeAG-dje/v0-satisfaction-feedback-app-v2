let bloqueado = false;

function registar(grau) {
    if (bloqueado) return;
    
    bloqueado = true;
    
    // Desativar botoes
    document.querySelectorAll('.btn').forEach(btn => btn.disabled = true);
    
    fetch('/registar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grau: grau })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Mostrar mensagem
            document.getElementById('buttons').style.display = 'none';
            document.getElementById('mensagem').style.display = 'block';
            
            // Voltar ao estado inicial apos 3 segundos
            setTimeout(() => {
                document.getElementById('buttons').style.display = 'flex';
                document.getElementById('mensagem').style.display = 'none';
                document.querySelectorAll('.btn').forEach(btn => btn.disabled = false);
                bloqueado = false;
            }, 3000);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        document.querySelectorAll('.btn').forEach(btn => btn.disabled = false);
        bloqueado = false;
    });
}
