const { writeFileSync } = require('node:fs');
const { resolve } = require('node:path');

const rawApiBaseUrl = process.env.API_BASE_URL;

if (!rawApiBaseUrl) {
  throw new Error('API_BASE_URL is required for a production build.');
}

let apiBaseUrl;
try {
  apiBaseUrl = new URL(rawApiBaseUrl);
} catch {
  throw new Error('API_BASE_URL must be a valid HTTPS URL.');
}

if (
  apiBaseUrl.protocol !== 'https:' ||
  apiBaseUrl.username ||
  apiBaseUrl.password ||
  apiBaseUrl.pathname !== '/' ||
  apiBaseUrl.search ||
  apiBaseUrl.hash
) {
  throw new Error('API_BASE_URL must be an origin-only HTTPS URL.');
}

const targetPath = resolve(__dirname, 'src/environments/environment.production.ts');
const contents = `export const environment = {
  production: true,
  apiBaseUrl: ${JSON.stringify(apiBaseUrl.origin)}
};
`;

writeFileSync(targetPath, contents, 'utf8');
