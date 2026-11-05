const { chromium } = require('./tools/node_modules/playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
    const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless:true, args:['--no-sandbox','--allow-file-access-from-files']});
    try {
        for (const [name, file, width, height] of [
            ['dashboard-desktop','dashboard',1440,1040], ['dashboard-tablet','dashboard',768,1024], ['dashboard-laptop','dashboard',1280,800], ['dashboard-mobile','dashboard',390,844],
            ['month-mobile','month',390,844], ['registration-mobile','registration',390,844], ['active-mobile','active',390,844], ['history-mobile','history',390,844], ['reports-mobile','reports',390,844], ['login-desktop','login',1440,950], ['login-mobile','login',390,844]
        ]) {
            const page = await browser.newPage({viewport:{width,height}, deviceScaleFactor:1});
            await page.goto(pathToFileURL(path.join(__dirname, 'rendered', file + '.html')).href);
            const brokenImages = await page.locator('img').evaluateAll(images => images.filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src));
            if (brokenImages.length) throw new Error(name + ': broken images ' + brokenImages.join(', '));
            await page.evaluate(() => document.fonts.ready);
            const layout = await page.evaluate(() => ({viewport:innerWidth, document:document.documentElement.scrollWidth}));
            if (layout.document > layout.viewport) throw new Error(name + ': horizontal overflow ' + JSON.stringify(layout));
            if (file !== 'login' && await page.locator('nav[aria-label="Administration"]').count()) throw new Error('Administration navigation should be hidden');
            if (width > 640 && file !== 'login') {
                for (const scrollY of [0, 300]) {
                    await page.evaluate(y => window.scrollTo(0, y), scrollY);
                    const position = await page.evaluate(() => {
                        const sidebar = document.querySelector('.app-sidebar').getBoundingClientRect();
                        const logout = document.querySelector('.logout-button').getBoundingClientRect();
                        return {gap: sidebar.bottom - logout.bottom, bottom: logout.bottom, viewport: innerHeight};
                    });
                    if (position.gap > 25 || position.gap < 0 || position.bottom > position.viewport) throw new Error('Sign out is not anchored at the sidebar bottom: ' + JSON.stringify(position));
                }
                await page.evaluate(() => window.scrollTo(0, 0));
            }
            if (width === 390 && file !== 'login') {
                const menu = page.locator('.mobile-menu');
                await menu.click();
                if (await menu.getAttribute('aria-expanded') !== 'true') throw new Error('Menu did not open');
                if (!await page.locator('#sidebar-navigation').isVisible()) throw new Error('Navigation not visible');
                await menu.click();
                if (await page.locator('#sidebar-navigation').isVisible()) throw new Error('Menu did not close');
            }
            if (file === 'registration') {
                const type = page.locator('#id_visitor_type');
                const detail = page.locator('#id_visitor_type_other');
                if (await detail.isVisible()) throw new Error('Other details should start hidden');
                await type.selectOption('Other');
                if (!await detail.isVisible() || !await detail.evaluate(el => el.required)) throw new Error('Other details must be visible and required');
                await detail.fill('Researcher');
                await type.selectOption('Guest');
                if (await detail.isVisible() || !await detail.isDisabled()) throw new Error('Other details should be disabled for Guest');
                await type.selectOption('Other');
                if (await detail.inputValue() !== 'Researcher') throw new Error('Typed details were lost when toggling');
                if (await page.locator('#id_office').evaluate(el => el.tagName) !== 'SELECT') throw new Error('Destination must be a dropdown');
                await type.selectOption('Guest');
                console.log('Other type: conditional field, required validation, toggle preservation and destination dropdown verified');
            }
            await page.screenshot({path:path.join(__dirname,name + '.png'),fullPage:true});
            console.log(name + ': no overflow; viewport=' + width + (width === 390 && file !== 'login' ? '; mobile menu opens and closes' : ''));
            await page.close();
        }
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
