import re, sys
GUARD = r'''
/* ===== Retour : le bouton retour d'Android et le glissement depuis le bord gauche (iPhone)
   ferment d'abord ce qui est ouvert, puis reviennent à l'accueil, au lieu de quitter l'app. ===== */
(function retourApp(C) {
  let arme = false, ignorer = false;
  const ouvert = () => { try { return C.couches.find(c => c[0]()); } catch (e) { return null; } };
  const besoin = () => { try { return !!ouvert() || !C.accueil(); } catch (e) { return false; } };
  const pop = () => { window.__retourPop = true; setTimeout(() => { window.__retourPop = false; }, 400); };
  const armer = () => {
    if (arme && !besoin()) { arme = false; ignorer = location.href; pop(); history.back(); return; }  // fermé depuis l'app : on retire l'entrée en trop
    if (!arme && besoin()) { try { history.pushState({ retourApp: 1 }, "", location.href); arme = true; } catch (e) {} }
  };
  const reculer = () => {
    try { const c = ouvert(); if (c) c[1](); else if (!C.accueil()) C.versAccueil(); } catch (e) {}
    setTimeout(armer, 450);
  };
  addEventListener("popstate", () => {
    pop();
    if (ignorer) { try { history.replaceState(null, "", ignorer); } catch (e) {} ignorer = false; return; }
    if (!arme) return;
    arme = false; reculer();
  });
  const verifier = () => setTimeout(armer, 80);
  ["click", "keyup", "touchend", "change"].forEach(t => document.addEventListener(t, verifier, true));
  let x0 = null, y0 = 0;
  document.addEventListener("touchstart", e => { const t = e.touches[0]; x0 = t.clientX < 24 ? t.clientX : null; y0 = t.clientY; }, { passive: true });
  document.addEventListener("touchend", e => {
    if (x0 == null) return; const t = e.changedTouches[0];
    if (t.clientX - x0 > 70 && Math.abs(t.clientY - y0) < 60 && besoin()) { if (arme) history.back(); else reculer(); }
    x0 = null;
  }, { passive: true });
  setTimeout(armer, 800);
})(%s);
'''
CODA = '{ couches: [[() => !!S.lesson, () => closeLesson()]], accueil: () => S.view === VIEWS[0], versAccueil: () => go(VIEWS[0]) }'
on = lambda sel: f'() => $("{sel}").classList.contains("on")'
CFG = {
 'matin': '{ couches: [[%s, () => closeModal()], [%s, () => openSheet(false)], [%s, () => closeOnAir()], [%s, () => closeArticle()]], accueil: () => state.nav === "home" && state.tab === "une", versAccueil: () => go({ nav: "home", tab: "une" }) }' % (on("#modal"), on("#sheet"), on("#onair"), on("#art")),
 'job': '{ couches: [[%s, () => openSheet(false)], [%s, () => closeArticle()]], accueil: () => state.nav === "home" && state.tab === "une", versAccueil: () => go({ nav: "home", tab: "une" }) }' % (on("#sheet"), on("#art")),
 'revision': '{ couches: [[%s, () => closeDrill()], [%s, () => closeSheet()], [%s, () => closeArticle()]], accueil: () => state.nav === "home" && state.tab === "une", versAccueil: () => go({ nav: "home", tab: "une" }) }' % (on("#drill"), on("#sheet"), on("#art")),
 'trail': '{ couches: [[() => sheet.classList.contains("on"), () => closeSheet()]], accueil: () => view === "home", versAccueil: () => go("home") }',
}
for k in ['bitabit', 'charpente', 'dodiese', 'miseenprod', 'rouille', 'socle']: CFG[k] = CODA

for name, cfg in CFG.items():
    s = open(f'{name}.html').read()
    assert 'retourApp' not in s, name
    scripts = list(re.finditer(r'(<script[^>]*>)(.*?)(</script>)', s, re.S))
    big = max(scripts, key=lambda m: len(m.group(2)))
    body = big.group(2)
    code = GUARD % cfg
    stripped = body.rstrip()
    if stripped.endswith('})();') and name in ('bitabit','charpente','dodiese','miseenprod','rouille','socle'):
        i = stripped.rfind('})();')
        body2 = stripped[:i] + code + stripped[i:] + body[len(stripped):]
    else:
        body2 = body + code
    # empêcher l'ancien routage par # de réagir pendant un retour
    body2 = body2.replace('window.addEventListener("hashchange", () => {', 'window.addEventListener("hashchange", () => { if (window.__retourPop) return;')
    body2 = body2.replace('addEventListener("hashchange", routeHash)', 'addEventListener("hashchange", () => { if (!window.__retourPop) routeHash(); })')
    s2 = s[:big.start(2)] + body2 + s[big.end(2):]
    open(f'out/{name}.html', 'w').write(s2)
    print(name, 'ok', len(s), '->', len(s2))
