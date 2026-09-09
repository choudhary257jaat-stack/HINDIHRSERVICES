"""Backend testing for SSR (Dynamic Rendering) + Sitemap endpoints.

Tests the NEW SEO bug fix: SSR-for-bots that serves full HTML with real job listings
to crawlers instead of empty SPA loader.
"""
import requests
import json
import xml.etree.ElementTree as ET
from typing import Optional

# Backend base URL from frontend/.env
BASE_URL = "https://employee-hub-596.preview.emergentagent.com/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name: str, detail: str = ""):
    msg = f"✅ {test_name}"
    if detail:
        msg += f": {detail}"
    test_results["passed"].append(msg)
    print(msg)

def log_fail(test_name: str, detail: str):
    msg = f"❌ {test_name}: {detail}"
    test_results["failed"].append(msg)
    print(msg)

def log_warning(test_name: str, detail: str):
    msg = f"⚠️  {test_name}: {detail}"
    test_results["warnings"].append(msg)
    print(msg)

# ============================================================================
# TEST 1: GET /api/render?path=/ with Googlebot UA
# ============================================================================
def test_render_home():
    print("\n" + "="*80)
    print("TEST 1: GET /api/render?path=/ (Googlebot UA)")
    print("="*80)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    
    try:
        resp = requests.get(f"{BASE_URL}/render?path=/", headers=headers, timeout=30)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("render home status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("render home status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            log_fail("render home content-type", f"Expected text/html, got {content_type}")
            return
        log_pass("render home content-type", "text/html")
        
        html = resp.text
        
        # Check for non-empty <title>
        if "<title>" not in html or "</title>" not in html:
            log_fail("render home title", "No <title> tag found")
            return
        title_start = html.find("<title>") + 7
        title_end = html.find("</title>")
        title = html[title_start:title_end].strip()
        if not title or len(title) < 5:
            log_fail("render home title", f"Title is empty or too short: '{title}'")
            return
        log_pass("render home title", f"Non-empty title found: '{title[:60]}...'")
        
        # Check for meta description
        if '<meta name="description"' not in html:
            log_fail("render home meta description", "No meta description found")
            return
        log_pass("render home meta description", "Found")
        
        # Check for canonical link
        if '<link rel="canonical"' not in html:
            log_fail("render home canonical", "No canonical link found")
            return
        log_pass("render home canonical", "Found")
        
        # Check for OG tags
        if 'property="og:title"' not in html:
            log_fail("render home og:title", "No og:title found")
            return
        log_pass("render home og:title", "Found")
        
        if 'property="og:description"' not in html:
            log_fail("render home og:description", "No og:description found")
            return
        log_pass("render home og:description", "Found")
        
        # Check for Twitter card
        if 'name="twitter:card"' not in html:
            log_fail("render home twitter:card", "No twitter:card found")
            return
        log_pass("render home twitter:card", "Found")
        
        # CRITICAL: Check for REAL job listing content (not just loader)
        # Look for multiple job entries with links to /vacancies/
        job_count = html.count('class="job"')
        vacancy_links = html.count('/vacancies/')
        
        if job_count < 5:
            log_fail("render home job listings", f"Expected multiple job entries, found only {job_count}")
            return
        log_pass("render home job listings", f"Found {job_count} job entries")
        
        if vacancy_links < 5:
            log_fail("render home vacancy links", f"Expected multiple /vacancies/ links, found only {vacancy_links}")
            return
        log_pass("render home vacancy links", f"Found {vacancy_links} vacancy links")
        
        # Check that it's not just a loader/empty root
        if "Loading" in html or "loading" in html:
            log_warning("render home loader", "HTML contains 'Loading' text - may be showing loader")
        
        if len(html) < 5000:
            log_warning("render home size", f"HTML is only {len(html)} bytes - may be incomplete")
        else:
            log_pass("render home size", f"{len(html)} bytes - substantial content")
        
    except Exception as e:
        log_fail("render home", f"Exception: {str(e)}")

# ============================================================================
# TEST 2: GET /api/render?path=/vacancies/{id} with social crawler UA
# ============================================================================
def test_render_vacancy_detail():
    print("\n" + "="*80)
    print("TEST 2: GET /api/render?path=/vacancies/{id} (Facebook UA)")
    print("="*80)
    
    # First, get a valid vacancy ID
    try:
        resp = requests.get(f"{BASE_URL}/vacancies?limit=1", timeout=15)
        if resp.status_code != 200:
            log_fail("get vacancy id", f"Failed to fetch vacancies: {resp.status_code}")
            return
        
        data = resp.json()
        # Response may be a list or a dict with "items"
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
        else:
            log_fail("get vacancy id", f"Unexpected response format: {type(data)}")
            return
        
        if not items:
            log_fail("get vacancy id", "No vacancies found in database")
            return
        
        vacancy_id = items[0].get("id")
        if not vacancy_id:
            log_fail("get vacancy id", "Vacancy has no 'id' field")
            return
        
        log_pass("get vacancy id", f"Got vacancy ID: {vacancy_id}")
        
    except Exception as e:
        log_fail("get vacancy id", f"Exception: {str(e)}")
        return
    
    # Now test the render endpoint
    headers = {
        "User-Agent": "facebookexternalhit/1.1"
    }
    
    try:
        resp = requests.get(f"{BASE_URL}/render?path=/vacancies/{vacancy_id}", headers=headers, timeout=30)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("render vacancy status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("render vacancy status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            log_fail("render vacancy content-type", f"Expected text/html, got {content_type}")
            return
        log_pass("render vacancy content-type", "text/html")
        
        html = resp.text
        
        # Check for JobPosting JSON-LD
        if 'application/ld+json' not in html:
            log_fail("render vacancy json-ld", "No JSON-LD script found")
            return
        
        if '"@type":"JobPosting"' not in html and '"@type": "JobPosting"' not in html:
            log_fail("render vacancy JobPosting", "No JobPosting schema found in JSON-LD")
            return
        log_pass("render vacancy JobPosting", "Found JobPosting JSON-LD schema")
        
        # Check for OG tags
        if 'property="og:title"' not in html:
            log_fail("render vacancy og:title", "No og:title found")
            return
        log_pass("render vacancy og:title", "Found")
        
        if 'property="og:image"' not in html:
            log_fail("render vacancy og:image", "No og:image found")
            return
        log_pass("render vacancy og:image", "Found")
        
        # Check for <h1> with post name
        if "<h1>" not in html:
            log_fail("render vacancy h1", "No <h1> tag found")
            return
        log_pass("render vacancy h1", "Found <h1> tag")
        
        # Check for unique title
        if "<title>" not in html:
            log_fail("render vacancy title", "No <title> tag found")
            return
        title_start = html.find("<title>") + 7
        title_end = html.find("</title>")
        title = html[title_start:title_end].strip()
        if not title:
            log_fail("render vacancy title", "Title is empty")
            return
        log_pass("render vacancy title", f"Unique title: '{title[:60]}...'")
        
        # Check for canonical link
        if '<link rel="canonical"' not in html:
            log_fail("render vacancy canonical", "No canonical link found")
            return
        log_pass("render vacancy canonical", "Found")
        
    except Exception as e:
        log_fail("render vacancy", f"Exception: {str(e)}")

# ============================================================================
# TEST 3: GET /api/render?path=/faq
# ============================================================================
def test_render_faq():
    print("\n" + "="*80)
    print("TEST 3: GET /api/render?path=/faq")
    print("="*80)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    
    try:
        resp = requests.get(f"{BASE_URL}/render?path=/faq", headers=headers, timeout=30)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("render faq status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("render faq status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            log_fail("render faq content-type", f"Expected text/html, got {content_type}")
            return
        log_pass("render faq content-type", "text/html")
        
        html = resp.text
        
        # Check for FAQPage JSON-LD (if FAQs exist)
        if 'application/ld+json' in html:
            if '"@type":"FAQPage"' in html or '"@type": "FAQPage"' in html:
                log_pass("render faq FAQPage", "Found FAQPage JSON-LD schema")
            else:
                log_warning("render faq FAQPage", "JSON-LD found but not FAQPage type")
        else:
            log_warning("render faq FAQPage", "No JSON-LD found (may be no FAQs in DB)")
        
        # Check it renders without error
        if "<title>" in html and len(html) > 1000:
            log_pass("render faq content", "Page renders successfully")
        else:
            log_warning("render faq content", "Page may be incomplete")
        
    except Exception as e:
        log_fail("render faq", f"Exception: {str(e)}")

# ============================================================================
# TEST 4: GET /api/render?path=/some-nonexistent-route-xyz (expect 404)
# ============================================================================
def test_render_nonexistent():
    print("\n" + "="*80)
    print("TEST 4: GET /api/render?path=/some-nonexistent-route-xyz (expect 404)")
    print("="*80)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    
    try:
        resp = requests.get(f"{BASE_URL}/render?path=/some-nonexistent-route-xyz", headers=headers, timeout=30)
        
        # Must be 404, NOT 500
        if resp.status_code == 404:
            log_pass("render nonexistent status", "404 as expected (unsupported route)")
        elif resp.status_code == 500:
            log_fail("render nonexistent status", "Got 500 instead of 404 - should return 404 for unsupported routes")
        else:
            log_fail("render nonexistent status", f"Expected 404, got {resp.status_code}")
        
    except Exception as e:
        log_fail("render nonexistent", f"Exception: {str(e)}")

# ============================================================================
# TEST 5: GET /api/sitemap.xml
# ============================================================================
def test_sitemap_xml():
    print("\n" + "="*80)
    print("TEST 5: GET /api/sitemap.xml")
    print("="*80)
    
    try:
        resp = requests.get(f"{BASE_URL}/sitemap.xml", timeout=30)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("sitemap status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("sitemap status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "application/xml" not in content_type and "text/xml" not in content_type:
            log_fail("sitemap content-type", f"Expected application/xml, got {content_type}")
            return
        log_pass("sitemap content-type", "application/xml")
        
        xml_content = resp.text
        
        # Check for valid XML structure
        if "<urlset" not in xml_content:
            log_fail("sitemap urlset", "No <urlset> tag found")
            return
        log_pass("sitemap urlset", "Found <urlset> tag")
        
        # Count <loc> entries
        loc_count = xml_content.count("<loc>")
        if loc_count < 10:
            log_fail("sitemap loc count", f"Expected many <loc> entries (hundreds), found only {loc_count}")
            return
        log_pass("sitemap loc count", f"Found {loc_count} <loc> entries")
        
        # Check for static pages
        static_pages = ["/services", "/solar", "/faq"]
        found_static = sum(1 for page in static_pages if page in xml_content)
        if found_static < 2:
            log_warning("sitemap static pages", f"Expected static pages, found only {found_static}")
        else:
            log_pass("sitemap static pages", f"Found {found_static} static pages")
        
        # Check for vacancy URLs
        if "/vacancies/" not in xml_content:
            log_fail("sitemap vacancy urls", "No /vacancies/ URLs found")
            return
        vacancy_url_count = xml_content.count("/vacancies/")
        log_pass("sitemap vacancy urls", f"Found {vacancy_url_count} vacancy URLs")
        
        # Check for blog URLs (if any)
        if "/blogs/" in xml_content:
            blog_url_count = xml_content.count("/blogs/")
            log_pass("sitemap blog urls", f"Found {blog_url_count} blog URLs")
        else:
            log_warning("sitemap blog urls", "No blog URLs found (may be no published blogs)")
        
        # Try to parse as XML
        try:
            ET.fromstring(xml_content)
            log_pass("sitemap xml parse", "Valid XML structure")
        except ET.ParseError as e:
            log_fail("sitemap xml parse", f"Invalid XML: {str(e)}")
        
    except Exception as e:
        log_fail("sitemap", f"Exception: {str(e)}")

# ============================================================================
# TEST 6: GET /api/sitemap-vacancies.xml
# ============================================================================
def test_sitemap_vacancies_xml():
    print("\n" + "="*80)
    print("TEST 6: GET /api/sitemap-vacancies.xml")
    print("="*80)
    
    try:
        resp = requests.get(f"{BASE_URL}/sitemap-vacancies.xml", timeout=30)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("sitemap-vacancies status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("sitemap-vacancies status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "application/xml" not in content_type and "text/xml" not in content_type:
            log_fail("sitemap-vacancies content-type", f"Expected application/xml, got {content_type}")
            return
        log_pass("sitemap-vacancies content-type", "application/xml")
        
        xml_content = resp.text
        
        # Check for valid XML structure
        if "<urlset" not in xml_content:
            log_fail("sitemap-vacancies urlset", "No <urlset> tag found")
            return
        log_pass("sitemap-vacancies urlset", "Found <urlset> tag")
        
        # Check for vacancy URLs
        if "/vacancies/" not in xml_content:
            log_fail("sitemap-vacancies vacancy urls", "No /vacancies/ URLs found")
            return
        vacancy_url_count = xml_content.count("/vacancies/")
        log_pass("sitemap-vacancies vacancy urls", f"Found {vacancy_url_count} vacancy URLs")
        
        # Try to parse as XML
        try:
            ET.fromstring(xml_content)
            log_pass("sitemap-vacancies xml parse", "Valid XML structure")
        except ET.ParseError as e:
            log_fail("sitemap-vacancies xml parse", f"Invalid XML: {str(e)}")
        
    except Exception as e:
        log_fail("sitemap-vacancies", f"Exception: {str(e)}")

# ============================================================================
# TEST 7: GET /api/robots.txt
# ============================================================================
def test_robots_txt():
    print("\n" + "="*80)
    print("TEST 7: GET /api/robots.txt")
    print("="*80)
    
    try:
        resp = requests.get(f"{BASE_URL}/robots.txt", timeout=15)
        
        # Check status code
        if resp.status_code != 200:
            log_fail("robots.txt status", f"Expected 200, got {resp.status_code}")
            return
        log_pass("robots.txt status", "200 OK")
        
        # Check Content-Type
        content_type = resp.headers.get("Content-Type", "")
        if "text/plain" not in content_type:
            log_fail("robots.txt content-type", f"Expected text/plain, got {content_type}")
            return
        log_pass("robots.txt content-type", "text/plain")
        
        content = resp.text
        
        # Check for "Allow: /api/sitemap.xml"
        if "Allow: /api/sitemap.xml" not in content:
            log_fail("robots.txt allow sitemap", "Missing 'Allow: /api/sitemap.xml' line")
            return
        log_pass("robots.txt allow sitemap", "Found 'Allow: /api/sitemap.xml'")
        
        # Check for "Sitemap: " pointing to /api/sitemap.xml
        if "Sitemap:" not in content or "/api/sitemap.xml" not in content:
            log_fail("robots.txt sitemap directive", "Missing 'Sitemap: .../api/sitemap.xml' line")
            return
        log_pass("robots.txt sitemap directive", "Found 'Sitemap: .../api/sitemap.xml'")
        
        # Check for "Disallow: /api/"
        if "Disallow: /api/" not in content:
            log_fail("robots.txt disallow api", "Missing 'Disallow: /api/' line")
            return
        log_pass("robots.txt disallow api", "Found 'Disallow: /api/'")
        
    except Exception as e:
        log_fail("robots.txt", f"Exception: {str(e)}")

# ============================================================================
# TEST 8: Regression sanity checks
# ============================================================================
def test_regression_sanity():
    print("\n" + "="*80)
    print("TEST 8: Regression sanity checks")
    print("="*80)
    
    # Test GET /api/vacancies?limit=5
    try:
        resp = requests.get(f"{BASE_URL}/vacancies?limit=5", timeout=15)
        if resp.status_code != 200:
            log_fail("regression vacancies", f"GET /api/vacancies?limit=5 returned {resp.status_code}")
        else:
            data = resp.json()
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
            elif isinstance(data, list):
                items = data
            else:
                log_fail("regression vacancies", f"Unexpected response format: {type(data)}")
                return
            
            if len(items) > 0:
                log_pass("regression vacancies", f"GET /api/vacancies?limit=5 returned {len(items)} items")
            else:
                log_warning("regression vacancies", "GET /api/vacancies?limit=5 returned 0 items")
    except Exception as e:
        log_fail("regression vacancies", f"Exception: {str(e)}")
    
    # Test GET /api/
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=15)
        if resp.status_code != 200:
            log_fail("regression api root", f"GET /api/ returned {resp.status_code}")
        else:
            data = resp.json()
            if "message" in data or "status" in data:
                log_pass("regression api root", f"GET /api/ returned ok message: {data}")
            else:
                log_warning("regression api root", f"GET /api/ returned unexpected format: {data}")
    except Exception as e:
        log_fail("regression api root", f"Exception: {str(e)}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*80)
    print("BACKEND TESTING: SSR (Dynamic Rendering) + Sitemap Endpoints")
    print("Testing NEW SEO bug fix: SSR-for-bots serving full HTML with real job listings")
    print("="*80)
    
    # Run all tests
    test_render_home()
    test_render_vacancy_detail()
    test_render_faq()
    test_render_nonexistent()
    test_sitemap_xml()
    test_sitemap_vacancies_xml()
    test_robots_txt()
    test_regression_sanity()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n✅ PASSED: {len(test_results['passed'])}")
    for msg in test_results['passed']:
        print(f"  {msg}")
    
    if test_results['warnings']:
        print(f"\n⚠️  WARNINGS: {len(test_results['warnings'])}")
        for msg in test_results['warnings']:
            print(f"  {msg}")
    
    if test_results['failed']:
        print(f"\n❌ FAILED: {len(test_results['failed'])}")
        for msg in test_results['failed']:
            print(f"  {msg}")
    else:
        print("\n🎉 ALL TESTS PASSED!")
    
    print("\n" + "="*80)
    print(f"TOTAL: {len(test_results['passed'])} passed, {len(test_results['failed'])} failed, {len(test_results['warnings'])} warnings")
    print("="*80)

if __name__ == "__main__":
    main()
