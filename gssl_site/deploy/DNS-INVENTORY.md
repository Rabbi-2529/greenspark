# greensparksolutions.com — DNS as observed, 26 November 2026

Read from public DNS from outside the zone, because nobody here has Cloudflare
access. **This is not a complete zone.** A DNS zone cannot be enumerated from
outside: every name below was guessed and then confirmed. Anything not guessed
— a verification TXT for some other service, a CNAME for a mail tool, a
subdomain for a client portal — is invisible here and would be silently lost
in a migration.

Before moving nameservers, get the real thing: Cloudflare → DNS → Records →
**Export** produces a BIND zone file with every record in one click. One
read-only look at that account removes all the guesswork below.

## Authority

| | |
|---|---|
| Registrar | Namecheap |
| Nameservers | `oswald.ns.cloudflare.com`, `pola.ns.cloudflare.com` |
| Created / expires | 2023-06-06 / 2027-06-06 |
| Status | `clientTransferProhibited` |

## Mail — Google Workspace

Losing these stops company email, including `info@greensparksolutions.com`.

    MX   1   ASPMX.L.GOOGLE.com
    MX   5   ALT1.ASPMX.L.GOOGLE.com
    MX   5   ALT2.ASPMX.L.GOOGLE.com
    MX  10   ALT3.ASPMX.L.GOOGLE.com
    MX  10   ALT4.ASPMX.L.GOOGLE.com

## TXT at the apex

    v=spf1 a mx ip4:134.119.179.229 ~all
    google-gws-recovery-domain-verification=45764387
    google-site-verification=OphkZjAD67cRtw4L051s-R4mWDiv7TgWe4NUgf4S6ZM

No DMARC record (`_dmarc`) and no DKIM at the `google`, `default`,
`selector1`, `selector2` or `k1` selectors.

**Two pre-existing problems, unrelated to this deployment but worth raising
with Green Spark.** The SPF record authorises `a`, `mx` and one IP address —
it does **not** include `_spf.google.com`, even though Google sends the
domain's mail. Mail from Google Workspace therefore fails SPF (softly, because
of `~all`). With no DKIM and no DMARC either, the domain's mail has no working
authentication at all, which costs deliverability. The fix is a one-line SPF
change plus turning on DKIM in the Google admin console, and it should happen
whoever ends up holding DNS.

## Hostnames

All of these answer on Cloudflare's proxy addresses (`104.21.91.12`,
`172.67.207.75`), so the real targets behind them cannot be read from outside.
There is **no wildcard record** — each name is defined individually.

| Name | Real target | Notes |
|---|---|---|
| `greensparksolutions.com` | DigitalOcean App Platform | the Next.js site; `x-do-app-origin` header |
| `www` | same | |
| `admin` | the droplet, port 3001 | has its own Let's Encrypt cert on the droplet |
| `ics` | the droplet, gunicorn socket | has its own Let's Encrypt cert on the droplet |
| `mail` | unknown | |
| `webmail` | unknown | |
| `smtp` | unknown | |
| `pop` | unknown | |
| `ftp` | unknown | |
| `cpanel` | unknown | |

The last six are almost certainly leftovers from a cPanel host — plausibly
`134.119.179.229`, the address the SPF record still names. Note they are
*proxied*: Cloudflare only proxies HTTP and HTTPS, so `smtp`, `pop` and
`webmail` cannot be working as mail endpoints today. Mail goes through Google,
so nothing depends on them, but copy them anyway to preserve the status quo.

## If DNS moves to Namecheap

Recreate, in this order, and verify each before switching nameservers if the
registrar lets you pre-stage records:

1. The five MX records, exactly as above.
2. The three apex TXT records, exactly as above.
3. `A @` and `A www` → `170.64.218.194` (the droplet).
4. `A admin` and `A ics` → `170.64.218.194`.
5. The six legacy names, once someone confirms where they should point.

Then expect up to **48 hours** of split resolution: a nameserver change sits
behind the registry's TTL, so some resolvers will still ask Cloudflare while
others ask Namecheap. Both answers must be correct for that whole window,
which is why the App Platform app should keep running throughout.

Leaving Cloudflare also means losing its TLS termination, CDN, WAF and the
hiding of the origin address. One upside: with the apex pointing straight at
the droplet, `certbot --nginx -d greensparksolutions.com -d
www.greensparksolutions.com` works normally and gives a publicly trusted
certificate, so the self-signed one can go.
