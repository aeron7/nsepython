module.exports = {
  title: 'NSEPython',
  description: 'NSEPython is a Python library to get publicly available data on NSE website ie. stock quotes, historical data, live indices, etc.',
  smoothScroll: true,
  base: '/docs/',
  themeConfig: {
    nav:[
        {text: 'Home', link: '/'},
        {text: 'Guide', link: '/guide/'},
        {text: 'Leverage', link: 'https://www.unofficed.com/leverage/'},
        {text: 'Feature Request', link: 'https://forum.unofficed.com/t/nsepython-discussion-and-feature-request/665/'},
        {text: 'Telegram', link: 'https://telegram.me/unofficed/'},
        {text: 'Github', link: 'https://github.com/aeron7/nsepython'}
        ],
    sidebar: {
        '/guide/': [
                    '',
                    'nsefetch',
                    'basic',
                    'custom',
                    'special'
                    ]
              }

  }
}
