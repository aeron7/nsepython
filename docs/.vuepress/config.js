module.exports = {
  title: 'NSEPython',
  description: 'NSEPython is a Python library to get publicly available data on NSE website ie. stock quotes, historical data, live indices, etc.',
  smoothScroll: true,
  base: '/nsepython/',
  head: [
    ['link', { rel: "apple-touch-icon", sizes: "180x180", href: "/images/favicon.jpg"}],
    ['link', { rel: "icon", type: "image/png", sizes: "32x32", href: "/images/favicon.jpg"}],
    ['link', { rel: "shortcut icon", href: "/images/favicon.jpg"}],
  ],
  themeConfig: {
    nav:[
        {text: 'Home', link: '/'},
        {text: 'Documentation', link: '/documentation/'},
        {text: 'Leverage', link: 'https://www.unofficed.com/leverage/'},
        {text: 'Feature Request', link: 'https://forum.unofficed.com/t/nsepython-discussion-and-feature-request/665/'},
        {text: 'Telegram', link: 'https://telegram.me/unofficed/'},
        {text: 'Github', link: 'https://github.com/aeron7/nsepython'}
        ],
    sidebar: {
        '/documentation/': [
                    '',
                    'nsefetch',
                    'basic',
                    'custom',
                    'special',
                    'nsetools'
                    ]
              }

  }
}
