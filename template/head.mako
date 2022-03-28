<%!
    from pdoc.html_helpers import minify_css
%>
<%def name="homelink()" filter="minify_css">
    .homelink {
        display: block;
        font-size: 2em;
        font-weight: bold;
        color: #555;
        padding-bottom: .5em;
        border-bottom: 1px solid silver;
    }
    .homelink:hover {
        color: inherit;
    }
    .homelink img {
        max-width:50%;
        max-height: 10em;
        margin: auto;
        margin-bottom: .3em;
    }
</%def>

<style>${homelink()}</style>
<link rel="canonical" href="file:///Users/ethanbrooks/monad_argparse/docs/dollar_lambda/index.html">
<link rel="icon" href="https://ethanabrooks.github.io/dollar-lambda/logo.png">
