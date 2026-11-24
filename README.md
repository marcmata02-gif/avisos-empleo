# Avisos de empleo · Barcelona (moda y belleza)

Revisa ofertas cada 30 minutos, se queda con las que encajan con tus criterios y te avisa por **Telegram**.

- **Web:** https://marcmata02-gif.github.io/avisos-empleo/ (pensada para el móvil; tus marcas y notas se guardan en el dispositivo donde las hagas)
- **Coste:** 0 € (GitHub Actions + GitHub Pages + Telegram + Gmail)

## Cómo funciona
| Fuente | Cómo llega |
|---|---|
| Webs de empleo de ~15 empresas (Puig, Pronovias, Veepee, Revlon, Meller, Nude Project…) | La app las lee directamente cada 30 min |
| LinkedIn | 8 alertas diarias → email a marcmata02@gmail.com → la app lo lee |
| Indeed, FashionJobs, FashionUnited, InfoJobs (opcional) | Crea alertas que lleguen a marcmata02@gmail.com y la app las leerá solas |
| InfoJobs y Adzuna por API (opcional) | Añade sus claves como secretos (`INFOJOBS_CLIENT_ID`, `INFOJOBS_CLIENT_SECRET`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) |

Las ofertas se guardan en la carpeta `datos/` del repositorio y la web lee `docs/ofertas.json`.

**Telegram:** te avisa una sola vez por oferta, solo de las publicadas en los últimos 7 días y solo de las que no llevan avisos ("Puede pedir más experiencia", "Jornada no indicada" o un idioma exigido). Las que llevan avisos se ven en la web.

**Secretos configurados en GitHub:** `TELEGRAM_BOT_TOKEN`, `GMAIL_USER` y `GMAIL_APP_PASSWORD`. Se cambian en Settings → Secrets and variables → Actions.

## Cambiar criterios
Abre en GitHub el archivo de la carpeta `config/`, pulsa el **lápiz ✏️**, haz el cambio y pulsa **Commit changes**. Se aplica en la siguiente revisión.
- `config/criterios.yaml`: áreas, palabras clave, descartes, nivel, idiomas, sectores, reglas de CV y opciones de Telegram.
- `config/empresas.yaml`: empresas y sus páginas de empleo. El archivo explica cómo añadir una.
- `config/fuentes.yaml`: frecuencias y búsquedas.

## Probar a mano
Actions → **Buscar ofertas** → **Run workflow**. Modos:
- `normal`: hace una revisión completa.
- `prueba`: muestra lo que encontraría, sin guardar ni avisar.
- `probar-telegram`: envía un mensaje de prueba al bot.

## 5. Lista de empresas (para que la revises)
70 empresas con oficinas en Barcelona y alrededores. Las 4 categorías que pediste están cubiertas: moda grande y mediana, moda pequeña, emergente, sostenible y nativa digital, belleza y cosmética, y agencias de PR, showrooms y distribuidores.

- ✅ **configurada**: su plataforma está confirmada y la app lee su página de empleo.
- 🟡 **configurada, por confirmar**: la app intenta leerla; la revisión de prueba te dirá si funciona.
- ⚪ **sin confirmar**: no he podido confirmar su página de empleo. La app no la consulta y sus ofertas llegan por LinkedIn, Indeed e InfoJobs. Muchas marcas pequeñas (Brava Fabrics, Thinking Mu, Lefrik...) no tienen página de empleo propia y publican solo en LinkedIn o en sus redes. Cuando encuentres la de alguna, cambia `plataforma` siguiendo las instrucciones de `empresas.yaml`. La web (al final, "Estado de las fuentes") muestra la lista de pendientes.

| Empresa | Sector | Tipo | Plataforma | Estado |
|---|---|---|---|---|
| Mango | Moda | Gran empresa | html | 🟡 configurada, por confirmar |
| Desigual | Moda | Gran empresa | successfactors | ✅ configurada |
| Pronovias | Moda | Gran empresa (nupcial) | teamtailor | ✅ configurada |
| Inditex (Stradivarius, Bershka, Oysho, Massimo Dutti) | Moda | Gran empresa | html | 🟡 configurada, por confirmar |
| Tous | Moda | Gran empresa (joyería) | pendiente | ⚪ sin confirmar (llega por portales) |
| Rosa Clará | Moda | Mediana (nupcial) | pendiente | ⚪ sin confirmar (llega por portales) |
| Custo Barcelona | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Munich | Moda | Mediana (calzado) | pendiente | ⚪ sin confirmar (llega por portales) |
| Sita Murt | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Bóboli | Moda | Mediana (infantil) | pendiente | ⚪ sin confirmar (llega por portales) |
| Veepee | Moda / Belleza | E-commerce de moda | lever | ✅ configurada |
| Mytheresa | Moda | E-commerce de lujo | successfactors | ✅ configurada |
| Punto Blanco | Moda | Mediana (ropa interior) | pendiente | ⚪ sin confirmar (llega por portales) |
| Lola Casademunt | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Simorra | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Escorpion | Moda | Mediana (punto) | pendiente | ⚪ sin confirmar (llega por portales) |
| Yerse | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Naulover | Moda | Mediana (punto) | pendiente | ⚪ sin confirmar (llega por portales) |
| Wom&Now | Moda | Mediana | pendiente | ⚪ sin confirmar (llega por portales) |
| Vertex Group | Moda | Diseño y producción para marcas | pendiente | ⚪ sin confirmar (llega por portales) |
| Natura (Natura Selection) | Moda / Belleza | Retail lifestyle (moda, regalo, cosmética) | pendiente | ⚪ sin confirmar (llega por portales) |
| Thomas Sabo (oficina Iberia) | Moda | Joyería internacional | html | 🟡 configurada, por confirmar |
| Swarovski (oficina Iberia) | Moda | Joyería internacional | pendiente | ⚪ sin confirmar (llega por portales) |
| Fabletics (oficina Europa) | Moda | Moda deportiva internacional | pendiente | ⚪ sin confirmar (llega por portales) |
| Brava Fabrics | Moda | Pequeña / sostenible | pendiente | ⚪ sin confirmar (llega por portales) |
| Thinking Mu | Moda | Pequeña / sostenible | pendiente | ⚪ sin confirmar (llega por portales) |
| Lefrik | Moda | Pequeña / sostenible (bolsos) | pendiente | ⚪ sin confirmar (llega por portales) |
| Paloma Wool | Moda | Pequeña / emergente | factorial | ✅ configurada |
| Meller | Moda | Nativa digital (gafas y accesorios) | factorial | ✅ configurada |
| Nude Project | Moda | Nativa digital (streetwear) | teamtailor | 🟡 configurada, por confirmar |
| PDPAOLA | Moda | Nativa digital (joyería) | pendiente | ⚪ sin confirmar (llega por portales) |
| Mr. Wonderful | Moda | Lifestyle / accesorios | pendiente | ⚪ sin confirmar (llega por portales) |
| Manebí | Moda | Pequeña (alpargatas de lujo) | pendiente | ⚪ sin confirmar (llega por portales) |
| Majoral | Moda | Pequeña (joyería) | pendiente | ⚪ sin confirmar (llega por portales) |
| Dominnico | Moda | Emergente (diseñador) | pendiente | ⚪ sin confirmar (llega por portales) |
| Lebor Gabala | Moda | Pequeña | pendiente | ⚪ sin confirmar (llega por portales) |
| Paez | Moda | Mediana (calzado) | pendiente | ⚪ sin confirmar (llega por portales) |
| Vasquiat | Moda | E-commerce de diseñadores | pendiente | ⚪ sin confirmar (llega por portales) |
| Wildpony | Moda | Nativa digital | pendiente | ⚪ sin confirmar (llega por portales) |
| YolanCris | Moda | Pequeña (nupcial) | pendiente | ⚪ sin confirmar (llega por portales) |
| Puig | Belleza / Moda | Gran empresa (belleza y moda) | successfactors | ✅ configurada |
| ISDIN | Belleza | Gran empresa (dermocosmética) | pendiente | ⚪ sin confirmar (llega por portales) |
| Natura Bissé | Belleza | Cosmética de lujo | pendiente | ⚪ sin confirmar (llega por portales) |
| Almirall | Belleza | Farmacéutica (dermatología) | successfactors | ✅ configurada |
| Uriach | Belleza | Salud natural y dermocosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Martiderm | Belleza | Dermocosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Cocunat | Belleza | Nativa digital (cosmética natural) | personio | ✅ configurada |
| Newflag | Belleza | Distribuidor (invisibobble, Tangle Teezer, Color Wow...) | personio | ✅ configurada |
| Olistic | Belleza | Nativa digital (cuidado capilar) | factorial | ✅ configurada |
| Revlon (oficina de Cornellà) | Belleza | Multinacional | greenhouse | ✅ configurada |
| Charlotte Tilbury | Belleza | Multinacional | workable | ✅ configurada |
| Beiersdorf (Nivea) | Belleza | Multinacional | pendiente | ⚪ sin confirmar (llega por portales) |
| Henkel Ibérica (Schwarzkopf) | Belleza | Multinacional | pendiente | ⚪ sin confirmar (llega por portales) |
| Pierre Fabre Ibérica | Belleza | Dermocosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| NAOS (Bioderma) | Belleza | Dermocosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Lacer | Belleza | Salud bucal y dermocosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Laboratorios Viñas | Belleza | Dermocosmética / farmacia | pendiente | ⚪ sin confirmar (llega por portales) |
| Byly | Belleza | Cosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Instituto Español | Belleza | Cosmética | pendiente | ⚪ sin confirmar (llega por portales) |
| Sepai | Belleza | Cosmética de lujo (pequeña) | pendiente | ⚪ sin confirmar (llega por portales) |
| Naturitas | Belleza | E-commerce (cosmética natural y salud) | pendiente | ⚪ sin confirmar (llega por portales) |
| Perfumerías Júlia | Belleza | Retail de perfumería | pendiente | ⚪ sin confirmar (llega por portales) |
| La Maison Comunicación | Moda / Belleza | Agencia de PR (moda, belleza, lifestyle) | pendiente | ⚪ sin confirmar (llega por portales) |
| Tal Cual Comunicación | Moda | Agencia de prensa y showroom de moda | pendiente | ⚪ sin confirmar (llega por portales) |
| Pressego Comunicación | Moda | Agencia de comunicación de moda | pendiente | ⚪ sin confirmar (llega por portales) |
| The Castle (agencia de influencia) | Moda / Belleza | Agencia boutique de marketing de influencia | pendiente | ⚪ sin confirmar (llega por portales) |
| Luxe Talent | Moda | Consultora de selección (moda, retail y lujo) | html | 🟡 configurada, por confirmar |
| Vlanc | Moda | Agencia comercial / showroom | pendiente | ⚪ sin confirmar (llega por portales) |
| The Fashion Hub (Moøde) | Moda | Showroom y coworking de marcas | pendiente | ⚪ sin confirmar (llega por portales) |
| Santa Eulalia | Moda | Multimarca de lujo | pendiente | ⚪ sin confirmar (llega por portales) |
Ideas para seguir ampliando la lista: las marcas de 080 Barcelona Fashion y del Clúster Català de la Moda (MODACC), la Asociación Moda Sostenible Barcelona (MSBCN) y las empresas que veas repetidas en tus alertas.

---

## Problemas frecuentes
| Problema | Solución |
|---|---|
| No llega nada a Telegram | Ejecuta el modo `probar-telegram`. Recuerda que las ofertas con avisos solo aparecen en la web. |
| `[gmail] ERROR` | La contraseña de aplicación ha cambiado o se ha revocado: crea otra y actualiza el secreto `GMAIL_APP_PASSWORD`. |
| Una empresa da error | En la web, mira "Estado de las fuentes". Si su página ha cambiado, pon `plataforma: pendiente` en `empresas.yaml`. |
| Demasiadas o muy pocas ofertas | Activa "Ver las que descartó el filtro" en la web y ajusta `criterios.yaml`. |
| GitHub dice que ha desactivado la tarea programada | Actions → Buscar ofertas → **Enable workflow**. |
