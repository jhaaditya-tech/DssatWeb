var map = L.map('map');
var adm1='';
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

function load_charts(admin1){
         window.location.href=window.location.protocol+'//'+window.location.host+'/charts/'+admin1+'/';

}



function whenClicked(e) {
        var admin1 = e.target.feature.properties.admin1;
        admin1="'"+admin1+"'";
    var popup = L.popup();
    popup.setLatLng(e.latlng)
         .setContent('<b>Selected Admin Region: </b>'
             + admin1
             +'<br><br>Clicking on the following button will show the baseline charts and allow you to work with yield, anomaly and stress charts.'
             + '<br><br><center><button id="charts" class="btn btn-secondary" onclick="load_charts('+admin1+')">Load charts</button>')
        .openOn(map);




}
function onEachFeature(feature, layer) {

    //bind click
    layer.on({
        click: whenClicked
    });

}
var  country_layer = L.geoJSON(shp_obj, {
                style: {
                    weight: 2,
                    opacity: 1,
                    color: '#000000',  //Outline color
                    fillOpacity: 0.2,
                     strokeWidth: 0,
                },
        onEachFeature: onEachFeature,
                // onEachFeature: onEachFeature_country,
            });

            country_layer.addTo(map);
            map.fitBounds(country_layer.getBounds());
