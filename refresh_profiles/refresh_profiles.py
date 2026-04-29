import asyncio
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# =========================
# Agregar raíz del proyecto
# =========================
root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from utils.seatable import Seatable
from config.logger import logger_general as logger

# =========================
# Cargar .env correctamente
# =========================
env_path = root_path / ".env"
load_dotenv(dotenv_path=env_path)


def get_env_var(*names):
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return value.strip()
    return None


# =========================
# Configuration
# =========================
INFLUENCER_API_TOKEN = get_env_var("INFLUENCER_API_TOKEN")
EMAIL_INSTAGRAM = get_env_var("EMAIL_INSTAGRAM", "email_instagram")
PASSWORD_INSTAGRAM = get_env_var("PASSWORD_INSTAGRAM", "password_instagram")
LEFTY_EMAIL = get_env_var("LEFTY_EMAIL", "lefty_email")
LEFTY_PASSWORD = get_env_var("LEFTY_PASSWORD", "lefty_password")

EXTENSION_PATH = os.path.abspath(
    os.path.join(os.getcwd(), "refresh_profiles", "extension")
)

CONCURRENCY_LIMIT = 1


# =========================
# Helpers UI
# =========================
async def human_sleep(min_s: float, max_s: float):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_type(locator, text: str):
    await locator.click()
    await locator.fill("")
    for char in text:
        await locator.type(char, delay=random.randint(60, 180))
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.1, 0.4))


async def is_visible(locator, timeout=1500):
    try:
        await locator.first.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


async def click_if_visible(locator, timeout=3000):
    try:
        await locator.first.wait_for(state="visible", timeout=timeout)
        await locator.first.click()
        return True
    except Exception:
        return False


async def click_first_visible(page, texts, timeout=2500):
    for text in texts:
        try:
            locator = page.get_by_text(text, exact=True)
            if await click_if_visible(locator, timeout=timeout):
                logger.info(f"Click realizado en texto: {text}")
                return True
        except Exception:
            pass
    return False


async def click_first_visible_button(page, names, timeout=2500):
    for name in names:
        try:
            locator = page.get_by_role("button", name=name)
            if await click_if_visible(locator, timeout=timeout):
                logger.info(f"Click realizado en botón: {name}")
                return True
        except Exception:
            pass
    return False


async def wait_network_idle_safe(page, timeout=5000):
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass


async def accept_instagram_cookies(page):
    for cookie_text in [
        "Allow all cookies",
        "Permitir todas las cookies",
        "Only allow essential cookies",
        "Permitir solo cookies esenciales",
    ]:
        try:
            if await click_first_visible_button(page, [cookie_text], timeout=2500):
                logger.info(f"Cookie popup aceptado: {cookie_text}")
                await human_sleep(0.8, 2.2)
                return
        except Exception:
            pass


async def dismiss_instagram_popups(page):
    popup_texts = [
        "Not Now",
        "Ahora no",
        "Save info",
        "Guardar información",
        "Turn on Notifications",
        "Activar notificaciones",
    ]

    for text in popup_texts:
        try:
            if await click_first_visible(page, [text], timeout=2000):
                await human_sleep(0.7, 1.8)
        except Exception:
            pass


# =========================
# Lefty helpers
# =========================
async def get_lefty_frame(page, timeout=15000):
    """
    Devuelve el iframe REAL de Lefty: https://plugin.lefty.io/...
    No el wrapper chrome-extension://...
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (timeout / 1000)

    while loop.time() < deadline:
        real_frame = None
        wrapper_frame = None

        for frame in page.frames:
            url = (frame.url or "").lower()

            if url.startswith("https://plugin.lefty.io"):
                real_frame = frame
                break

            if url.startswith("chrome-extension://") and "plugin.lefty.io" in url:
                wrapper_frame = frame

        if real_frame:
            logger.info(f"Lefty frame real detectado: {real_frame.url}")
            return real_frame

        if wrapper_frame:
            logger.info(f"Solo se ve wrapper frame por ahora: {wrapper_frame.url}")

        await asyncio.sleep(random.uniform(0.15, 0.45))

    raise RuntimeError("No se encontró el iframe real de Lefty (https://plugin.lefty.io).")


async def lefty_panel_is_open(frame):
    open_signals = [
        frame.locator('lefty-icon[icon="close"]'),
        frame.locator('lefty-icon.close-dialog'),
        frame.locator('input[type="email"]'),
        frame.locator('input[type="password"]'),
        frame.get_by_text("Collect stories", exact=True),
        frame.get_by_text("Sign In", exact=True),
        frame.get_by_role("button", name="Sign In"),
    ]

    for locator in open_signals:
        if await is_visible(locator, timeout=600):
            return True

    return False


async def open_lefty_panel(page):
    frame = await get_lefty_frame(page)

    for attempt in range(4):
        if await lefty_panel_is_open(frame):
            logger.info("Lefty ya está abierto.")
            return frame

        logger.info(f"Intentando abrir el panel de Lefty... (Intento {attempt + 1})")

        open_btn = frame.locator(
            'lefty-icon[icon="arrow_right"], lefty-icon.open, i.lefty-icon-i.lefty-icons:has-text("arrow_right")'
        ).first

        try:
            await open_btn.wait_for(state="attached", timeout=4000)
            await open_btn.scroll_into_view_if_needed()
            logger.info("Esperando antes de hacer clic para abrir el panel...")
            await human_sleep(1.5, 3.5)
            await open_btn.click(force=True)
            logger.info("Se hizo clic en el botón para abrir Lefty.")
        except Exception as e:
            logger.debug(f"Botón no encontrado o error en clic: {e}")

        await human_sleep(1.5, 3.5)

    return frame


async def lefty_needs_login(frame):
    email_input = frame.locator('input[type="email"], input[name="email"]').first
    password_input = frame.locator('input[type="password"], input[name="password"]').first

    email_visible = await is_visible(email_input, timeout=1200)
    password_visible = await is_visible(password_input, timeout=1200)

    return email_visible and password_visible


async def login_lefty_if_needed(page):
    """
    Si Lefty no está logueado, llena el formulario con LEFTY_EMAIL / LEFTY_PASSWORD.
    """
    frame = await open_lefty_panel(page)

    if not await lefty_needs_login(frame):
        logger.info("Lefty ya está autenticado o no muestra login.")
        return frame

    if not LEFTY_EMAIL or not LEFTY_PASSWORD:
        raise ValueError("Faltan LEFTY_EMAIL o LEFTY_PASSWORD en el archivo .env")

    logger.info("Lefty requiere login. Llenando credenciales...")

    email_input = frame.locator('input[type="email"], input[name="email"]').first
    password_input = frame.locator('input[type="password"], input[name="password"]').first
    sign_in_btn = frame.locator(
        'button:has-text("Sign In"), [role="button"]:has-text("Sign In")'
    ).first

    await email_input.wait_for(state="visible", timeout=10000)
    await password_input.wait_for(state="visible", timeout=10000)

    await human_type(email_input, LEFTY_EMAIL)
    await human_sleep(0.5, 1.2)
    await human_type(password_input, LEFTY_PASSWORD)

    await sign_in_btn.wait_for(state="visible", timeout=5000)
    await human_sleep(0.4, 1.0)
    await sign_in_btn.click()

    logger.info("Login de Lefty enviado.")
    await human_sleep(1.5, 3.5)

    return frame


async def wait_for_collect_stories(frame, timeout=20000):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (timeout / 1000)

    while loop.time() < deadline:
        btn = frame.get_by_text("Collect stories", exact=True)
        if await is_visible(btn, timeout=500):
            return btn.first
        await asyncio.sleep(random.uniform(0.3, 0.8))

    await asyncio.sleep(90)

    return None


async def wait_and_click_ok(page, timeout=15000):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (timeout / 1000)

    while loop.time() < deadline:
        for target in [page] + page.frames:
            try:
                ok_btn = target.get_by_role("button", name="OK")
                if await is_visible(ok_btn, timeout=400):
                    logger.info("Popup OK detectado, esperando antes del clic...")
                    await human_sleep(1.5, 3.0)
                    await ok_btn.first.click()
                    return True
            except Exception:
                pass

        await asyncio.sleep(random.uniform(0.3, 0.8))

    return False


async def ensure_lefty_ready(page):
    frame = await login_lefty_if_needed(page)

    collect_btn = await wait_for_collect_stories(frame, timeout=20000)
    if not collect_btn:
        raise RuntimeError("Lefty no quedó listo: no apareció 'Collect stories' a tiempo.")

    logger.info("Lefty está listo.")
    return frame


# =========================
# Instagram state machine
# =========================
async def detect_instagram_state(page):
    try:
        current_url = (page.url or "").lower()
        t_fast = 500

        # 1) Pantalla de cuenta guardada
        if (
            await is_visible(page.get_by_role("button", name="Continuar"), timeout=t_fast)
            or await is_visible(page.get_by_role("button", name="Continue"), timeout=t_fast)
            or await is_visible(page.get_by_text("Usar otro perfil", exact=True), timeout=t_fast)
            or await is_visible(page.get_by_text("Use another account", exact=True), timeout=t_fast)
        ):
            return "account_chooser"

        # 2) Formulario de login
        username_visible = await is_visible(
            page.locator('input[name="username"], input[autocomplete="username"], input[name="email"]'),
            timeout=t_fast
        )
        password_visible = await is_visible(
            page.locator('input[name="password"], input[type="password"], input[name="pass"]'),
            timeout=t_fast
        )

        if username_visible or password_visible:
            return "login_form"

        # 3) Modal invitado
        if await is_visible(page.locator('div[role="dialog"]'), timeout=t_fast):
            if (
                await is_visible(page.get_by_text("Regístrate", exact=True), timeout=300)
                or await is_visible(page.get_by_text("Sign up", exact=True), timeout=300)
            ):
                return "guest_modal"

        if "instagram.com/accounts/login" in current_url:
            return "login_form"

        if "instagram.com/" in current_url:
            return "logged_in"

        return "unknown"
    except Exception:
        return "unknown"


async def log_instagram_state(page, prefix="Instagram state"):
    state = await detect_instagram_state(page)
    logger.info(f"{prefix}: {state} | URL: {page.url}")
    return state


# =========================
# Instagram auth flow
# =========================
async def open_instagram_login_page(page):
    await page.goto(
        "https://www.instagram.com/accounts/login/",
        wait_until="domcontentloaded",
        timeout=90000
    )
    await human_sleep(1.5, 3.5)
    await accept_instagram_cookies(page)
    await wait_network_idle_safe(page, timeout=10000)
    return await log_instagram_state(page, prefix="Estado al abrir login page")


async def force_login_form(page):
    state = await open_instagram_login_page(page)

    if state == "account_chooser":
        clicked = await click_first_visible(
            page,
            ["Usar otro perfil", "Use another account"],
            timeout=3000
        )

        if not clicked:
            clicked = await click_first_visible_button(
                page,
                ["Usar otro perfil", "Use another account"],
                timeout=3000
            )

        await human_sleep(1.5, 3.5)
        state = await log_instagram_state(page, prefix="Estado después de 'Usar otro perfil'")

    if state != "login_form":
        state = await log_instagram_state(page, prefix="Estado antes de validar login_form")

    if state != "login_form":
        raise RuntimeError(
            f"No se pudo llegar al formulario real de login. Estado detectado: {state}"
        )


async def do_instagram_login_form(page):
    if not EMAIL_INSTAGRAM or not PASSWORD_INSTAGRAM:
        raise ValueError(
            "No se cargaron las credenciales de Instagram. "
            "Revisa el .env con EMAIL_INSTAGRAM y PASSWORD_INSTAGRAM."
        )

    logger.info(f"Archivo .env cargado desde: {env_path}")
    logger.info(f"EMAIL_INSTAGRAM cargado: {bool(EMAIL_INSTAGRAM)}")
    logger.info(f"PASSWORD_INSTAGRAM cargado: {bool(PASSWORD_INSTAGRAM)}")

    username_input = page.locator(
        'input[name="username"], input[autocomplete="username"], input[name="email"]'
    ).first
    password_input = page.locator(
        'input[name="password"], input[type="password"], input[name="pass"]'
    ).first
    submit_button = page.locator(
        'button[type="submit"], '
        'div[role="button"][aria-label="Iniciar sesión"], '
        'div[role="button"][aria-label="Log in"], '
        'button:has-text("Iniciar sesión"), '
        'button:has-text("Log in"), '
        'div:has-text("Iniciar sesión")[role="button"], '
        'div:has-text("Log in")[role="button"]'
    ).first

    await username_input.wait_for(state="visible", timeout=30000)
    await password_input.wait_for(state="visible", timeout=30000)

    await human_type(username_input, EMAIL_INSTAGRAM)
    await human_sleep(0.6, 1.5)
    await human_type(password_input, PASSWORD_INSTAGRAM)

    logger.info("Credenciales escritas en el formulario de Instagram.")

    try:
        await submit_button.wait_for(state="visible", timeout=5000)
        await human_sleep(0.4, 1.0)
        await submit_button.click()
        logger.info("Click realizado en el botón de login.")
    except Exception:
        logger.info("No se pudo hacer click en el botón de login (timeout o no visible). Intentando 'Enter' en el campo de password.")
        await password_input.press("Enter")

    await wait_network_idle_safe(page, timeout=30000)
    await human_sleep(4.0, 7.5)

    await dismiss_instagram_popups(page)

    state_after = await log_instagram_state(page, prefix="Estado después de enviar login")

    if state_after in {"login_form", "guest_modal", "account_chooser"}:
        raise RuntimeError(
            f"Instagram sigue mostrando una pantalla de acceso después del login. Estado: {state_after}"
        )


async def ensure_instagram_authenticated(page, profile_url=None):
    state = await log_instagram_state(page, prefix="Estado inicial de Instagram")

    if state == "logged_in":
        logger.info("Instagram ya estaba autenticado.")
        return True

    if state == "account_chooser":
        logger.info("Se detectó pantalla de cuenta guardada.")

        clicked_continue = await click_first_visible_button(
            page, ["Continuar", "Continue"], timeout=3000
        )
        await human_sleep(4.0, 7.0)
        await wait_network_idle_safe(page, timeout=5000)

        state = await log_instagram_state(page, prefix="Estado después de intentar 'Continuar'")

        if clicked_continue and state == "logged_in":
            if profile_url:
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=50000)
                await wait_network_idle_safe(page, timeout=5000)
                await human_sleep(0.8, 2.0)
                await log_instagram_state(page, prefix="Estado después de volver al perfil")
            return True

        await force_login_form(page)
        await do_instagram_login_form(page)

        if profile_url:
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=50000)
            await wait_network_idle_safe(page, timeout=5000)
            await human_sleep(0.8, 2.0)

        final_state = await log_instagram_state(page, prefix="Estado final luego de login desde chooser")
        return final_state == "logged_in"

    if state == "guest_modal":
        logger.info("Se detectó modal de invitado.")

        clicked_login = await click_first_visible(page, ["Iniciar sesión", "Log in"], timeout=3000)

        if not clicked_login:
            await force_login_form(page)
        else:
            await human_sleep(1.5, 3.5)
            state = await log_instagram_state(page, prefix="Estado después de click en 'Iniciar sesión'")
            if state != "login_form":
                await force_login_form(page)

        await do_instagram_login_form(page)

        if profile_url:
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=50000)
            await wait_network_idle_safe(page, timeout=5000)
            await human_sleep(0.8, 2.0)

        final_state = await log_instagram_state(page, prefix="Estado final luego de guest_modal")
        return final_state == "logged_in"

    if state == "login_form":
        logger.info("Se detectó formulario de login.")
        await do_instagram_login_form(page)

        if profile_url:
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=50000)
            await wait_network_idle_safe(page, timeout=5000)
            await human_sleep(0.8, 2.0)

        final_state = await log_instagram_state(page, prefix="Estado final luego de login_form")
        return final_state == "logged_in"

    logger.info("Estado unknown; se fuerza apertura del formulario.")
    await force_login_form(page)
    await do_instagram_login_form(page)

    if profile_url:
        await page.goto(profile_url, wait_until="domcontentloaded", timeout=50000)
        await wait_network_idle_safe(page, timeout=5000)
        await human_sleep(0.8, 2.0)

    final_state = await log_instagram_state(page, prefix="Estado final luego de unknown")
    return final_state == "logged_in"


# =========================
# Worker por influencer
# =========================
async def process_influencer(influencer, context, semaphore, platforms_to_visit):
    async with semaphore:
        page = await context.new_page()

        try:
            name = influencer.get("Source", "Unknown")
            social_accounts = influencer.get("Social Accounts", [])

            links_to_visit = []
            for account in social_accounts:
                url = account.get("display_value", "")
                for platform in platforms_to_visit:
                    if platform.lower() in url.lower():
                        links_to_visit.append((platform, url))

            if not links_to_visit:
                return {"Source": name, "success": True, "status": "No links found", "visited": 0}

            logger.info(f"Processing influencer: {name}")

            success_count = 0
            errors = []

            for platform, url in links_to_visit:
                try:
                    logger.info(f"Visiting {platform} link for {name}: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=50000)
                    await wait_network_idle_safe(page, timeout=5000)
                    await human_sleep(0.8, 2.5)

                    if platform.lower() == "instagram":
                        authenticated = await ensure_instagram_authenticated(page, profile_url=url)
                        if not authenticated:
                            raise RuntimeError("No fue posible autenticar la sesión de Instagram.")

                        logger.info(f"Instagram autenticado correctamente para {name}.")

                        logger.info(f"Preparing Lefty for {name}...")
                        lefty_frame = await ensure_lefty_ready(page)

                        collect_btn = await wait_for_collect_stories(lefty_frame, timeout=5000)

                        if collect_btn:
                            logger.info("Botón 'Collect stories' detectado, simulando actividad antes del clic...")
                            await page.mouse.wheel(0, random.randint(80, 350))
                            await human_sleep(0.4, 1.0)
                            await page.mouse.move(
                                random.randint(350, 650),
                                random.randint(250, 550),
                                steps=random.randint(5, 15),
                            )
                            await human_sleep(1.0, 2.5)
                            await collect_btn.click()
                            logger.info(f"Clicked 'Collect stories' for {name}")

                            logger.info(f"Waiting for confirmation for {name}")
                            confirmed = await wait_and_click_ok(page, timeout=15000)

                            if confirmed:
                                logger.info(f"Successfully collected stories for {name}")
                                success_count += 1
                            else:
                                errors.append(f"{platform}: Confirmation popup not found")
                        else:
                            errors.append(f"{platform}: Collect stories button not found")

                except PlaywrightTimeoutError as e:
                    error_msg = f"{platform}: Timeout - {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"{platform}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            cooldown = random.uniform(8.0, 25.0)
            logger.info(f"Inter-account cooldown: {cooldown:.1f}s")
            await asyncio.sleep(cooldown)

            status = "Success" if not errors else f"Errors: {', '.join(errors)}"
            return {
                "Source": name,
                "success": len(errors) == 0,
                "status": status,
                "visited": success_count,
            }

        finally:
            try:
                await page.close()
            except Exception:
                pass


# =========================
# Main
# =========================
async def main(platforms_to_visit):
    logger.info("Connecting to SeaTable...")

    if not INFLUENCER_API_TOKEN:
        raise ValueError("Falta INFLUENCER_API_TOKEN en el archivo .env")

    st = Seatable(INFLUENCER_API_TOKEN)

    query = """
    SELECT `_id`, `Source`, `Social Accounts`
    FROM `Influencer Info`
    WHERE `Tracked` = 'Yes'
    """
    influencers = st.sql_query(query)

    logger.info(f"Found {len(influencers)} tracked influencers.")

    if not influencers:
        logger.info("No influencers to process.")
        return

    user_data_dir = os.path.abspath(
        os.path.join(os.getcwd(), "temp", "playwright", "main_session")
    )
    os.makedirs(user_data_dir, exist_ok=True)

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                f"--disable-extensions-except={EXTENSION_PATH}",
                f"--load-extension={EXTENSION_PATH}",
                "--start-maximized",
            ],
            no_viewport=True,
        )

        results = []
        try:
            bootstrap_page = context.pages[0] if context.pages else await context.new_page()

            # Login base Instagram una sola vez
            await bootstrap_page.goto(
                "https://www.instagram.com/",
                wait_until="domcontentloaded",
                timeout=50000
            )
            await wait_network_idle_safe(bootstrap_page, timeout=5000)
            await human_sleep(0.8, 2.5)

            authenticated = await ensure_instagram_authenticated(
                bootstrap_page,
                profile_url="https://www.instagram.com/"
            )
            if not authenticated:
                raise RuntimeError("No fue posible autenticar Instagram en la página base.")

            logger.info("Instagram base autenticado.")

            # Login base Lefty una sola vez
            await login_lefty_if_needed(bootstrap_page)
            logger.info("Lefty base autenticado.")

            tasks = [
                process_influencer(influencer, context, semaphore, platforms_to_visit)
                for influencer in influencers
            ]

            results = []
            for i, task in enumerate(tasks):
                result = await task
                results.append(result)
                if (i + 1) % 10 == 0 and (i + 1) < len(tasks):
                    pause = random.uniform(60, 180)
                    logger.info(f"Session pause after {i + 1} accounts: {pause:.0f}s")
                    await asyncio.sleep(pause)

        finally:
            try:
                await context.close()
            except Exception:
                pass

    total = len(results)
    successes = sum(1 for r in results if r["success"])
    failures = total - successes

    print("\n" + "=" * 50)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 50)
    print(f"Total procesados: {total}")
    print(f"Exitosos: {successes}")
    print(f"Fallidos: {failures}")
    print("-" * 50)

    if failures > 0:
        print("Detalle de errores:")
        for r in results:
            if not r["success"]:
                print(f"- {r['Source']}: {r['status']}")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    platforms = ["instagram"]
    asyncio.run(main(platforms))