# Avisos de empleo · Barcelona (moda y belleza)

Esta app personal revisa ofertas de trabajo cada 30 minutos, se queda con las que encajan con tus criterios y te avisa por **Telegram**. Además tienes una **web privada** pensada para el móvil, donde puedes consultar las ofertas y marcarlas.

**Coste: 0 €.** Todo funciona con planes gratuitos:

| Pieza | Servicio gratuito | Para qué |
|---|---|---|
| Revisión cada 30 min | GitHub Actions (repositorio **público** = minutos ilimitados) | Ejecuta la búsqueda |
| Base de datos | Supabase (plan Free) | Guarda las ofertas y tus marcas |
| Web | GitHub Pages | Lista de ofertas en el móvil |
| Avisos | Bot de Telegram | Mensaje por cada oferta nueva |
| LinkedIn, Indeed, FashionJobs, FashionUnited | Sus alertas por email → una cuenta de Gmail dedicada (IMAP) | Sin scraping |
| InfoJobs, Adzuna | Sus API oficiales gratuitas | Búsquedas en la provincia de Barcelona |
| Webs de empresas | Endpoints públicos (Greenhouse, Lever, Workable, Personio, Teamtailor, SuccessFactors, Workday, Factorial...) o lectura ligera | Ofertas en origen |

> **Privacidad:** el repositorio es público, pero **no contiene tu perfil**. Solo están los criterios de búsqueda, los nombres de tus versiones de CV y la lista de empresas. Las claves van en "secretos" de GitHub. La web pide iniciar sesión y solo deja entrar a tu email. Ojo: los registros de ejecución de GitHub Actions de un repositorio público también son públicos. En ellos solo aparecen títulos de ofertas y contadores, nunca emails ni claves.

---

## 1. Lo que no es posible (y la alternativa)

- **"En cuanto se publiquen" en LinkedIn e Indeed.** La app no entra en LinkedIn ni en Indeed (como pediste). Depende de cuándo te envían ellos las alertas: normalmente una vez al día o en tandas. La app las lee en un máximo de 30 minutos después de que lleguen. Las fuentes que sí se consultan directamente cada 30 min son las webs de empresas, InfoJobs (cada hora, por prudencia con su cuota) y Adzuna (cada 4 h, por su cuota gratuita).
- **Las alertas de LinkedIn e InfoJobs llegan al email de tu cuenta**, no al Gmail dedicado. Solución: un filtro de reenvío automático en tu email personal hacia el Gmail dedicado (paso 10). El reenvío conserva el remitente original, que es lo que la app necesita.
- **GitHub Actions no es puntual.** Las tareas programadas pueden retrasarse entre 5 y 20 minutos en horas punta. Además, GitHub las desactiva si el repositorio pasa 60 días sin cambios. El propio flujo hace un commit vacío cada 45 días para evitarlo.
- **RSS de FashionJobs.** No he encontrado un RSS público de ofertas, ni en FashionJobs ni en FashionUnited (solo de noticias). Por eso se usan sus alertas por email. Si encuentras un feed, añádelo en `config/fuentes.yaml` → `rss`.
- **API de InfoJobs.** Es oficial y gratuita, pero InfoJobs no indica si sigue aceptando aplicaciones nuevas. Si no puedes registrarte, crea alertas de InfoJobs por email y reenvíalas al Gmail. La app ya las entiende ("InfoJobs (alerta)").
- **Lectura de emails.** El formato de los emails de alertas puede cambiar sin aviso. Si un día dejan de llegar ofertas de un portal, mira "Estado de las fuentes" en la web y avísame (o abre un *issue*).
- **Webs de empresas no comprobadas en vivo.** No he podido conectarme a ellas desde mi entorno. Están escritas siguiendo el formato público de cada plataforma, y algunas (Puig, Pronovias, Meller, Veepee) las he consultado por otra vía. Haz la **revisión de prueba** del paso 9: te dirá qué empresas funcionan y cuáles dan error.
- **Datos que la oferta no trae.** Las ofertas que llegan por email traen poco texto, así que ahí "Qué piden", salario o idioma suelen salir vacíos. Si la misma oferta aparece también en InfoJobs o en la web de la empresa, se fusionan y se completa.
- **Supabase Free** pausa los proyectos inactivos una semana. Como la app escribe cada 30 minutos, nunca llega a estar inactivo.

---

## 2. Qué hace exactamente

1. Cada 30 min, GitHub Actions ejecuta `python -m jobwatch.main`.
2. Lee las fuentes que tocan según `config/fuentes.yaml`.
3. **Une duplicados.** La misma oferta en varios portales (misma empresa y mismo puesto, aunque cambie "(H/M)", "- Barcelona" o "S.L.") queda como **una sola oferta con todos sus enlaces**. El primero es el de la web de la empresa, después InfoJobs, LinkedIn, Indeed...
4. **Filtra** con `config/criterios.yaml`: área, sector, nivel, jornada, prácticas, tienda, ubicación, años de experiencia, idiomas.
5. **Etiqueta** cada oferta con área y sector, avisos (nivel, idioma, jornada no indicada), CV recomendado, resumen de una línea, requisitos y salario.
6. **Avisa por Telegram** de las ofertas nuevas, destacando 🎓 graduate programs y 👗 moda:
   - Solo se avisa una vez por oferta (queda registrado en la base de datos).
   - Las ofertas con algún aviso ("Puede pedir más experiencia", "Jornada no indicada", "Exige francés"...) **solo aparecen en la web**, como elegiste.
   - Solo se avisa de ofertas de los últimos 7 días. El primer día no te llegará una avalancha.
7. Guarda todo en Supabase para la web.

### La web
- Lista de la más reciente a la más antigua, con "hace X h". Las de moda llevan borde granate y los graduate programs, azul.
- Pestañas Nuevas / Guardadas / Aplicadas / Descartadas / Todas.
- Buscador, filtros por área, sector, empresa y portal, y "Solo graduate programs".
- Al marcar **Aplicada** puedes elegir **con qué CV aplicaste** y añadir notas.
- "Ver las que descartó el filtro" enseña lo que se ha quedado fuera en los últimos 30 días y el motivo. Sirve para ajustar los criterios.
- "Estado de las fuentes" (al final) muestra la última revisión de cada fuente, sus errores y las empresas pendientes de configurar.

### Recomendación de CV (en `criterios.yaml` → `cv.reglas`)
| Situación | CV |
|---|---|
| Graduate program de belleza o de trade, en español | 5 · Iberia Trade Graduate / Marketing de Marca |
| Trade marketing, retail marketing, activación | 4 · Trade Marketing (si la oferta es en inglés, te lo indica y sugiere el 2) |
| Graduate program en inglés | 1 (si es de contenido o e-commerce) o 2 |
| Contenido, redes sociales, storytelling, e-commerce | 1 en inglés · 3 en español |
| Brand marketing de belleza en español | 5 |
| Marketing digital, marca | 2 en inglés · 3 en español |
| PR, prensa, influencers, compras, ofertas mixtas | 6 · CV general |

El idioma de la oferta se detecta automáticamente. Se aplica la primera regla que coincide y puedes cambiarlas.

---

## 3. Puesta en marcha paso a paso

Necesitas unos 60-90 minutos la primera vez. No hace falta saber programar: todo se hace desde el navegador.

### Paso 1 · Crear el repositorio en GitHub y subir el código
1. Crea una cuenta en <https://github.com> (gratis) si no la tienes.
2. Arriba a la derecha, **+ → New repository**. Nombre: `avisos-empleo` (o el que quieras). Marca **Public**. Pulsa **Create repository**.
3. Descomprime el zip que te he dado. En la página del repositorio pulsa **uploading an existing file** y arrastra **todo el contenido** de la carpeta (no la carpeta en sí).
   - ⚠️ La carpeta `.github` empieza por punto y está oculta. En Mac, en Finder pulsa `Cmd + Shift + .` para verla. En Windows: Explorador → Vista → Mostrar → Elementos ocultos. Sin esa carpeta no hay revisión automática.
4. Pulsa **Commit changes**.
5. Comprueba que en el repositorio ves las carpetas `.github`, `config`, `jobwatch`, `supabase`, `web` y `tests`.

### Paso 2 · Crear el bot de Telegram
1. En Telegram busca **@BotFather** (con la marca azul de verificado) y escríbele `/newbot`.
2. Te pide un nombre (p. ej. `Mis ofertas BCN`) y un usuario que termine en `bot` (p. ej. `ofertas_bcn_ana_bot`).
3. BotFather te da un **token** del tipo `123456789:AAH...`. Guárdalo: es `TELEGRAM_BOT_TOKEN`.
4. Abre el chat con tu bot nuevo y pulsa **Iniciar** (o escríbele "hola").
5. En el navegador abre `https://api.telegram.org/botTU_TOKEN/getUpdates`, cambiando `TU_TOKEN` por el token. Busca `"chat":{"id":` seguido de un número, p. ej. `"chat":{"id":987654321`. Ese número es `TELEGRAM_CHAT_ID`.
   - Si sale `"result":[]`, vuelve a escribir al bot y recarga la página.

### Paso 3 · Crear la base de datos (Supabase)
1. Entra en <https://supabase.com> → **Start your project**. Regístrate (puedes hacerlo con tu cuenta de GitHub).
2. **New project**. Nombre: `avisos-empleo`. Inventa una contraseña de base de datos (no la usarás). Región: **Europe (Frankfurt o Ireland)**. Plan **Free**.
3. Cuando esté listo, menú izquierdo → **SQL Editor** → **New query**. Pega **todo** el contenido del archivo `supabase/schema.sql` y pulsa **Run**. Debe decir *Success*.
4. Menú → **Project Settings** (engranaje) → **API Keys**:
   - **Publishable key** (`sb_publishable_...`) → `SUPABASE_PUBLISHABLE_KEY` (puede ser pública: la usa la web).
   - **Secret key** (`sb_secret_...`, pulsa "Reveal" o "Create new secret key") → `SUPABASE_SECRET_KEY`. **Nunca la compartas.**
5. **Project Settings → Data API** (o la pestaña "General"): copia la **Project URL**, del tipo `https://abcdefgh.supabase.co`. Es `SUPABASE_URL`.

### Paso 4 · Permitir solo tu acceso a la web
1. En Supabase → **Authentication → Users → Add user → Create new user**. Pon tu email personal (el que usarás para entrar en la web), marca *Auto Confirm User* y pulsa crear. La contraseña da igual: entrarás con un enlace por email.
2. **SQL Editor → New query**, pega esto (con tu email) y pulsa **Run**:
   ```sql
   insert into public.allowed_users (email) values ('TU_EMAIL_PERSONAL@ejemplo.com');
   ```
3. **Authentication → Sign In / Providers**: desactiva **Allow new users to sign up**. Así nadie más puede registrarse.
4. **Authentication → URL Configuration**: en **Site URL** pon la dirección de tu web, `https://TU_USUARIO_GITHUB.github.io/avisos-empleo/`. Añade esa misma dirección en **Redirect URLs**. Si tu repositorio se llama distinto, cambia `avisos-empleo`.

### Paso 5 · Gmail dedicado para las alertas
1. Crea una cuenta nueva de Gmail, p. ej. `ofertas.bcn.tunombre@gmail.com`.
2. Activa la verificación en dos pasos: <https://myaccount.google.com/security> → **Verificación en dos pasos**. Es obligatoria para lo siguiente.
3. Crea una **contraseña de aplicación** en <https://myaccount.google.com/apppasswords>. Nombre: `avisos-empleo`. Google te da 16 letras: es `GMAIL_APP_PASSWORD` (quita los espacios). El email es `GMAIL_USER`.
4. El acceso IMAP de Gmail viene activado. Si en Gmail → ⚙️ → Ver todos los ajustes → *Reenvío y correo POP/IMAP* ves una opción "Habilitar IMAP", márcala.
5. La app pone la etiqueta `ofertas-procesadas` a cada email que ya ha leído. No hace falta que borres nada.

### Paso 6 · Claves de InfoJobs y Adzuna
**InfoJobs**
1. Entra en <https://developer.infojobs.net> e inicia sesión con tu cuenta de InfoJobs (o crea una).
2. Ve a **Mis aplicaciones / Registrar aplicación**. Nombre: `avisos-empleo`. Uso: personal. Si te pide una URL de callback, pon `https://localhost`.
3. Copia el **Client ID** → `INFOJOBS_CLIENT_ID` y el **Client Secret** → `INFOJOBS_CLIENT_SECRET`.
4. Si no te deja registrar la aplicación, sáltate este paso y crea alertas de InfoJobs por email (paso 10). La app sigue funcionando.

**Adzuna**
1. Regístrate en <https://developer.adzuna.com> (**Register**, gratis y sin tarjeta).
2. En el panel (**Dashboard / API access details**) verás **Application ID** → `ADZUNA_APP_ID` y **Application Key** → `ADZUNA_APP_KEY`.
3. La configuración usa unas 24 llamadas al día, por debajo de la cuota gratuita.

### Paso 7 · Guardar las claves en GitHub (secretos)
En tu repositorio: **Settings → Secrets and variables → Actions → New repository secret**. Crea uno por fila; el nombre debe ser exacto:

| Nombre | Valor |
|---|---|
| `SUPABASE_URL` | Project URL (paso 3) |
| `SUPABASE_SECRET_KEY` | Secret key `sb_secret_...` |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key `sb_publishable_...` |
| `TELEGRAM_BOT_TOKEN` | token del bot (paso 2) |
| `TELEGRAM_CHAT_ID` | número del chat (paso 2) |
| `GMAIL_USER` | el Gmail dedicado |
| `GMAIL_APP_PASSWORD` | las 16 letras (paso 5) |
| `INFOJOBS_CLIENT_ID` | (si lo tienes) |
| `INFOJOBS_CLIENT_SECRET` | (si lo tienes) |
| `ADZUNA_APP_ID` | Application ID |
| `ADZUNA_APP_KEY` | Application Key |

Después, en la pestaña **Variables** de esa misma pantalla → **New repository variable**: nombre `WEB_URL`, valor `https://TU_USUARIO_GITHUB.github.io/avisos-empleo/`. Sirve para el botón "Ver en la web" de Telegram.

Si alguna fuente no tiene sus claves, simplemente se salta.

### Paso 8 · Publicar la web
1. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Pestaña **Actions**. Si ves un aviso para activar los workflows, pulsa **I understand my workflows, go ahead and enable them**.
3. A la izquierda elige **Publicar web** → **Run workflow** → **Run workflow**. En 1-2 min estará en `https://TU_USUARIO_GITHUB.github.io/avisos-empleo/`.
4. Ábrela en el móvil, pon tu email y pulsa el enlace que te llega. Ábrelo en el mismo móvil. Si quieres, en Safari o Chrome usa "Añadir a pantalla de inicio".

### Paso 9 · Probar y arrancar
En **Actions → Buscar ofertas → Run workflow**:
1. Modo **probar-telegram** → te llega "✅ Bot de ofertas conectado".
2. Modo **prueba** → no guarda ni avisa. Abre la ejecución → *buscar* → *Revisar fuentes* y verás:
   - una línea por fuente y empresa (`OK` o `ERROR` con el motivo);
   - las ofertas que pasarían el filtro (✔ con sector, área y CV);
   - un resumen de motivos de descarte.
   Si una empresa da error, cambia su `plataforma` a `pendiente` en `config/empresas.yaml` o corrige la dirección.
3. Modo **normal** → primera revisión real. Desde ahí se ejecuta sola cada 30 minutos.

### Paso 10 · Crear las alertas de empleo
Todas apuntan al **Gmail dedicado**, directamente o reenviadas. Incluye "moda"/"fashion" o "belleza"/"beauty" en las palabras clave siempre que puedas: la app usa el asunto del email para saber el sector cuando la empresa es desconocida.

**Reenvío desde tu email personal** (LinkedIn e InfoJobs envían las alertas al email de tu cuenta). En tu Gmail personal:
1. ⚙️ → Ver todos los ajustes → **Reenvío y correo POP/IMAP** → **Añadir una dirección de reenvío**. Pon el Gmail dedicado y confirma el código que llega allí.
2. **Filtros y direcciones bloqueadas → Crear un filtro**. En *De* pon `jobalerts-noreply@linkedin.com OR jobs-noreply@linkedin.com OR infojobs.net`. Luego **Crear filtro** → **Reenviar a** el Gmail dedicado (opcional: *Omitir Recibidos*).

Si tu email personal es Outlook: Configuración → Correo → Reglas → nueva regla con "Redirigir a". Usa *redirigir*, no *reenviar*, para que se mantenga el remitente.

**LinkedIn** (Empleos → busca → activa **Crear alerta**). En todas: Ubicación `Barcelona, Cataluña, España`. Filtros: **Tipo de empleo: Jornada completa**; **Nivel de experiencia: Sin experiencia + Algo de responsabilidad** (no marques Prácticas). Frecuencia: la más alta que te ofrezca (diaria), con notificación por email.

| # | Palabras clave (cópialas tal cual) |
|---|---|
| 1 | `(marketing OR brand) AND (moda OR fashion OR lujo OR luxury)` |
| 2 | `"trade marketing" OR "retail marketing" OR "brand activation" OR "shopper marketing"` |
| 3 | `(comunicación OR communications OR content OR contenido OR "social media") AND (moda OR fashion)` |
| 4 | `(PR OR "relaciones públicas" OR "press office" OR influencer OR showroom) AND (moda OR fashion OR beauty)` |
| 5 | `(buyer OR "assistant buyer" OR merchandiser OR compras OR "merchandise planner") AND (moda OR fashion)` |
| 6 | `(ecommerce OR "e-commerce" OR "online merchandiser" OR marketplace) AND (moda OR fashion)` |
| 7 | `(graduate OR trainee OR "early careers") AND (marketing OR brand OR fashion OR beauty)` |
| 8 | `(marketing OR "trade marketing" OR communications OR PR OR ecommerce) AND (beauty OR belleza OR cosmetics OR cosmética OR skincare OR fragrance)` |

**Indeed** (<https://es.indeed.com>). Busca *Qué* = la frase, *Dónde* = `Barcelona, Barcelona provincia`. Aplica el filtro **Tipo de jornada → Jornada completa** y pulsa **Recibir empleos nuevos por email** con el **Gmail dedicado** (en Indeed no hace falta reenvío).

| # | Qué |
|---|---|
| 1 | `marketing moda` |
| 2 | `fashion marketing` |
| 3 | `trade marketing` |
| 4 | `comunicación moda` |
| 5 | `social media moda` |
| 6 | `relaciones públicas moda` |
| 7 | `buyer moda` |
| 8 | `ecommerce moda` |
| 9 | `graduate marketing` |
| 10 | `marketing cosmética` |
| 11 | `marketing belleza` |

**FashionJobs** (<https://es.fashionjobs.com>). Crea una cuenta **con el Gmail dedicado** y crea alertas con Ubicación **Barcelona** para las categorías **Marketing / Comunicación**, **Compras / Producto** y **E-commerce / Digital**. Si deja palabras clave, añade una con `graduate` y otra con `PR`.

**FashionUnited** (<https://fashionunited.es/ofertas-trabajo-moda>). Filtra por **Barcelona** y por las categorías de marketing, comunicación, compras y e-commerce. Pulsa **Crear alerta** con el Gmail dedicado.

**InfoJobs** (solo si no tienes la API). Crea alertas con estas búsquedas: `marketing moda`, `trade marketing`, `comunicación moda`, `compras moda`, `ecommerce moda` y `marketing cosmética`. Filtros: provincia **Barcelona** y **Jornada completa**. Reenvía las alertas con el filtro de arriba.

---

## 4. Editar los criterios sin tocar el código
Todo está en la carpeta `config/`. En GitHub abre el archivo, pulsa el **lápiz ✏️**, cambia lo que quieras y pulsa **Commit changes**. En la siguiente revisión se aplica y se re-evalúan las ofertas de los últimos 30 días.

- `config/criterios.yaml`: áreas y sus palabras (en castellano, catalán e inglés), graduate programs, nivel (descartes y aviso de "manager"), máximo de años de experiencia (3), idiomas con aviso, descartes de tienda, comerciales, laboratorio, prácticas y jornada (en el **título**), excepciones (p. ej. "online store"), sectores y marcas conocidas, reglas de CV y opciones de Telegram.
- `config/fuentes.yaml`: frecuencia de cada fuente, búsquedas de InfoJobs y Adzuna, y feeds RSS.
- `config/empresas.yaml`: la lista de empresas. Para añadir una, copia un bloque. El propio archivo explica cómo saber su plataforma mirando la dirección de una oferta.

Reglas importantes que ya están implementadas:
- Las palabras de tienda (dependiente, store manager, beauty advisor...) solo se miran en el **título**. Un puesto de trade marketing que habla de "activaciones en tienda" pasa.
- Un **graduate program** se mantiene aunque sea un contrato de 1 año o el título diga "Head of ... Graduate", pero no si es beca o prácticas con convenio.
- "Manager" sin "junior" ni "assistant" → aviso **Puede pedir más experiencia**.
- Más de 3 años de experiencia pedidos → descartada. Se detectan frases como "5+ years", "mínimo 4 años", "3-5 años" (aquí cuenta el mínimo) o "al menos 4 años".
- Idioma distinto de castellano, catalán o inglés exigido → aviso. Si dice "valorable" o "a plus", no hay aviso.
- Jornada no indicada → aviso. En las alertas de LinkedIn e Indeed se asume jornada completa porque las creas con ese filtro.
- Contratos temporales y sustituciones (maternity cover) se descartan, excepto en graduate programs. Si quieres verlos, cambia `descartar_contrato_temporal: false`.
- Compras solo cuenta en moda. Belleza solo en marketing, trade marketing, comunicación, PR, contenido y e-commerce.

---

## 5. Lista de empresas (para que la revises)
70 empresas con oficinas en Barcelona y alrededores. Las 4 categorías que pediste están cubiertas: moda grande y mediana, moda pequeña, emergente, sostenible y nativa digital, belleza y cosmética, y agencias de PR, showrooms y distribuidores.

- ✅ **configurada**: su plataforma está confirmada y la app lee su página de empleo.
- 🟡 **configurada, por confirmar**: la app intenta leerla; la revisión de prueba te dirá si funciona.
- ⚪ **sin confirmar**: no he podido confirmar su página de empleo. La app no la consulta y sus ofertas llegan por LinkedIn, Indeed e InfoJobs. Muchas marcas pequeñas (Brava Fabrics, Thinking Mu, Lefrik...) no tienen página de empleo propia y publican solo en LinkedIn o en sus redes. Cuando encuentres la de alguna, cambia `plataforma` siguiendo las instrucciones de `empresas.yaml`. La web te muestra siempre la lista de pendientes.

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

## 6. Problemas frecuentes
| Problema | Solución |
|---|---|
| No llega nada a Telegram | Ejecuta el modo `probar-telegram`. Si falla, revisa `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` y que hayas escrito al bot. Recuerda que las ofertas con avisos solo van a la web. |
| `[gmail] ERROR ... AUTHENTICATIONFAILED` | La contraseña de aplicación está mal o falta la verificación en dos pasos. |
| La web dice "Error al cargar" | No has añadido tu email en `allowed_users` (paso 4.2) o has entrado con otro email. |
| El enlace del email de acceso no funciona | Revisa la *Site URL* y las *Redirect URLs* (paso 4.4) y ábrelo en el mismo navegador donde lo pediste. |
| Una empresa da ERROR cada vez | Su web ha cambiado. Pon `plataforma: pendiente` o corrige la `url`. |
| Demasiadas o muy pocas ofertas | Mira "Ver las que descartó el filtro" en la web y ajusta las palabras en `criterios.yaml`. |
| Se ha desactivado la revisión automática | Actions → Buscar ofertas → **Enable workflow**. |

## 7. Para quien sepa programar
- `python -m jobwatch.main --prueba [--fuente infojobs|adzuna|gmail|empresas|<empresa>]`
- Pruebas: `pip install -r requirements.txt pytest && pytest`. Son 30 pruebas sin red (filtros, emails, plataformas y el flujo completo con base de datos simulada).
- Código: `jobwatch/classify.py` (filtros), `jobwatch/dedupe.py` (duplicados), `jobwatch/sources/` (fuentes), `jobwatch/main.py` (flujo), `web/` (web estática con supabase-js).
