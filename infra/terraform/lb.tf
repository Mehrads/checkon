# The public domain in front of Cloud Run (infra/README.md, step 5). Cloud Run's own domain mapping isn't
# offered in Toronto, so a global external Application Load Balancer serves the domain through a serverless
# network endpoint group, with a Google-managed certificate. Created only once `domain` is set; about $18 a month.

locals {
  lb = var.domain != "" ? 1 : 0
}

resource "google_compute_global_address" "web" {
  count      = local.lb
  name       = "${local.name}-ip"
  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "app" {
  count                 = local.lb
  name                  = "${local.name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.app.name
  }
}

resource "google_compute_backend_service" "app" {
  count                 = local.lb
  name                  = "${local.name}-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.app[0].id
  }
}

# Issued once the domain's DNS points at the address above; until then HTTPS fails to connect.
resource "google_compute_managed_ssl_certificate" "web" {
  count = local.lb
  name  = "${local.name}-cert"

  managed {
    domains = [var.domain, "www.${var.domain}"]
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_ssl_policy" "web" {
  count           = local.lb
  name            = "${local.name}-tls"
  profile         = "MODERN"
  min_tls_version = "TLS_1_2"
  depends_on      = [google_project_service.apis]
}

resource "google_compute_url_map" "https" {
  count           = local.lb
  name            = "${local.name}-https"
  default_service = google_compute_backend_service.app[0].id

  # www sends visitors to the bare domain, so the site has one address.
  host_rule {
    hosts        = ["www.${var.domain}"]
    path_matcher = "www"
  }

  path_matcher {
    name = "www"

    default_url_redirect {
      host_redirect          = var.domain
      redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
      strip_query            = false
    }
  }
}

resource "google_compute_target_https_proxy" "web" {
  count            = local.lb
  name             = "${local.name}-https"
  url_map          = google_compute_url_map.https[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.web[0].id]
  ssl_policy       = google_compute_ssl_policy.web[0].id
}

resource "google_compute_global_forwarding_rule" "https" {
  count                 = local.lb
  name                  = "${local.name}-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.web[0].id
  port_range            = "443"
  target                = google_compute_target_https_proxy.web[0].id
}

# Plain HTTP only redirects to HTTPS.

resource "google_compute_url_map" "http" {
  count = local.lb
  name  = "${local.name}-http"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_target_http_proxy" "web" {
  count   = local.lb
  name    = "${local.name}-http"
  url_map = google_compute_url_map.http[0].id
}

resource "google_compute_global_forwarding_rule" "http" {
  count                 = local.lb
  name                  = "${local.name}-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.web[0].id
  port_range            = "80"
  target                = google_compute_target_http_proxy.web[0].id
}
