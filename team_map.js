(function() {
    // Prevent crazy redraw updates on resize
    d3.select(window).on('resize', throttle);

    var zoom = d3.behavior.zoom()
        .scaleExtent([1, 9])
        .on('zoom', move);

    var width = document.getElementById('container').offsetWidth;
    var height = width / 2;

    var topoC, topoL, projection, path, svg, g;
    var graticule = d3.geo.graticule();

    // XXX Tooltips later?

    setup(width, height);
    function setup(width, height) {
        projection = d3.geo.mercator()
            .scale((width + 1) / 2 / Math.PI)
            .translate([width / 2, height / 2])
            .precision(.1);

        path = d3.geo.path()
            .projection(projection);

        svg = d3.select('#container').append('svg')
            .attr('width', width)
            .attr('height', height)
            .call(zoom)
            .on('click', click)
            .append('g')

        g = svg.append('g');
    }

    d3.json('geo/world-50m.json', function(error, world) {
        if (error) throw error;
        console.log(world);

        var countries = topojson.mesh(world,
                                      world.objects.countries,
                                      function (a, b) { return a !== b; });
        var land = topojson.feature(world,
                                    world.objects.land);
        topoC = countries;
        topoL = land;

        draw(topoC, topoL); // Extend to recruits
    });

    function draw(topoC, topoL) {
        // Render latlon lines
        svg.append('path')
            .datum(graticule)
            .attr('class', 'graticule')
            .attr('d', path);

        // Render landmasses
        svg.insert('path', '.graticule')
            .datum(topoL)
            .attr('class', 'land')
            .attr('d', path);

        // Render world political borders
        svg.insert('path', '.graticule')
            .datum(topoC)
            .attr('class', 'boundary')
            .attr('d', path);

        // TODO: Render state/provincial political borders for US/CANADA
    }

    function redraw() {
        width = document.getElementById('container').offsetWidth;
        height = width / 2;
        d3.select('svg').remove();
        setup(width, height);
        draw(topoC, topoL);
    }

    function move() {
        var t = d3.event.translate;
        var s = d3.event.scale;
        zscale = s;
        var h = height / 4;

        t[0] = Math.min((width / height) * (s - 1),
                        Math.max(width * (1 - s), t[0]));
        t[1] = Math.min(h * (s-1) + (h * s),
                        Math.max(height * (1 - s) - (h * s), t[1]));

        zoom.translate(t);
        g.attr('transform', 'translate(' + t + ')scale(' + s + ')');
    }

    // Delay redraws
    var throttleTimer;
    function throttle() {
        window.clearTimeout(throttleTimer);
        throttleTimer = window.setTimeout(function() {
            redraw();
        }, 200);
    }

    // Geo translation on mouse click in map
    function click() {
        var latlon = projection.invert(d3.mouse(this));
        console.log(latlon);
    }

    // ==================================
    // Roster callback. This takes the roster index we build and
    // uses it to populate our comparison tool
    function rosterCallback(rosterPages) {
        console.log(rosterPages);
    };

    // Build roster index
    var rosterPages = [];
    d3.html('test-rosters', function(e, d) {
        var lis = d3.select(d).selectAll('li').selectAll('a');
        lis.forEach(function(v) {
            rosterPages.push(v[0].text)
        });

        rosterCallback(rosterPages);
    });
})();
