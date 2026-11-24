<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>accessibility_isochrones</Name>
    <UserStyle>
      <Title>Walking Isochrones Style</Title>
      <Abstract>Graduated semi-transparent blue fills for 5, 10, and 15-minute pedestrian catchments</Abstract>
      <FeatureTypeStyle>
        <!-- 5-minute isochrone: Deepest Blue -->
        <Rule>
          <Name>5_Min_Isochrone</Name>
          <Title>5-Minute Walk</Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>cutoff_minutes</ogc:PropertyName>
              <ogc:Literal>5</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#1d4ed8</CssParameter>
              <CssParameter name="fill-opacity">0.45</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1e40af</CssParameter>
              <CssParameter name="stroke-width">1.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>

        <!-- 10-minute isochrone: Medium Blue -->
        <Rule>
          <Name>10_Min_Isochrone</Name>
          <Title>10-Minute Walk</Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>cutoff_minutes</ogc:PropertyName>
              <ogc:Literal>10</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#3b82f6</CssParameter>
              <CssParameter name="fill-opacity">0.30</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#2563eb</CssParameter>
              <CssParameter name="stroke-width">1.2</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>

        <!-- 15-minute isochrone: Light Blue -->
        <Rule>
          <Name>15_Min_Isochrone</Name>
          <Title>15-Minute Walk</Title>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>cutoff_minutes</ogc:PropertyName>
              <ogc:Literal>15</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#93c5fd</CssParameter>
              <CssParameter name="fill-opacity">0.20</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#60a5fa</CssParameter>
              <CssParameter name="stroke-width">1.0</CssParameter>
              <CssParameter name="stroke-dasharray">4 2</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
