# Lluvia

Web app instalable (PWA) para iPhone con sonidos para dormir: lluvia suave, tormenta, mar, ruido marrón y ruido blanco. Bucles de 5 minutos sin cortes, temporizador de apagado y controles en la pantalla de bloqueo.

## Publicarla en GitHub Pages

1. En GitHub, crea un repositorio público llamado `lluvia`.
2. En el repo: **Add file → Upload files**, arrastra todo el contenido de esta carpeta (`index.html`, `manifest.json`, `sw.js`, `README.md` y las carpetas `iconos` y `sonidos`) y pulsa **Commit changes**.
3. **Settings → Pages → Source: Deploy from a branch → Branch: `main` / `(root)` → Save.**
4. En un minuto estará en `https://<tu-usuario>.github.io/lluvia/`.

## Instalarla en el iPhone

1. Abre esa dirección en **Safari** (tiene que ser Safari).
2. Botón **Compartir → Añadir a pantalla de inicio → Añadir**.
3. Ábrela desde el icono de la luna.

## Uso

- Toca un sonido y el botón grande.
- El volumen va con los botones físicos del iPhone (iOS no deja cambiarlo desde una web).
- "Apagar tras" para el sonido solo. Si algún día el temporizador no salta con la pantalla bloqueada, usa como respaldo **Reloj → Temporizador → Al terminar → Detener reproducción**.

## Regenerar o cambiar los sonidos

Los audios son sintéticos (generados con Python/NumPy, sin derechos de terceros). Para añadir uno propio: pon un `.m4a` en `sonidos/` y añade su botón en `index.html` y su nombre en el objeto `SONIDOS`.
