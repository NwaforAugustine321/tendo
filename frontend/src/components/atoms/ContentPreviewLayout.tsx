import { useEffect } from "react";
import {
  pdfLayoutStyles,
  groupByPage,
  compareElements,
  PdfElement,
} from "../../lib/parser_layout_converter";

const pdfJson: any = {
  "file name": "01030000000043.pdf",
  "number of pages": 1,
  author: null,
  title: null,
  "creation date": null,
  "modification date": null,
  kids: [
    {
      type: "paragraph",
      id: 4,
      "page number": 1,
      "bounding box": [70.795, 698.276, 275.533, 770.466],
      font: "Montserrat-Bold",
      "font size": 10,
      "text color": "[0.77, 0.25, 0.0, 0.0]",
      content:
        "Figure 7: Respondents’ reaction to the statement “I am worried that misogynistic and hostile beliefs espoused by extremist groups result in violence towards women.”",
    },
    {
      type: "image",
      id: 10,
      "page number": 1,
      "bounding box": [197.667, 626.104, 251.943, 680.832],
    },
    {
      type: "image",
      id: 16,
      "page number": 1,
      "bounding box": [89.282, 640.684, 144.363, 677.539],
    },
    {
      type: "paragraph",
      id: 9,
      "page number": 1,
      "bounding box": [224.227, 638.971, 268.23, 674.294],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "36% STRONGLY AGREE",
    },
    {
      type: "heading",
      id: 14,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [89.741, 654.564, 116.019, 670.047],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.77, 0.25, 0.0, 0.0]",
      content: "56%",
    },
    {
      type: "paragraph",
      id: 15,
      "page number": 1,
      "bounding box": [89.741, 645.254, 117.999, 654.812],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "AGREE",
    },
    {
      type: "image",
      id: 5,
      "page number": 1,
      "bounding box": [106.651, 512.556, 247.101, 653.003],
    },
    {
      type: "image",
      id: 11,
      "page number": 1,
      "bounding box": [78.348, 528.787, 166.234, 582.769],
    },
    {
      type: "image",
      id: 12,
      "page number": 1,
      "bounding box": [148.493, 498.302, 192.407, 582.769],
    },
    {
      type: "image",
      id: 13,
      "page number": 1,
      "bounding box": [202.276, 522.751, 274.273, 563.769],
    },
    {
      type: "heading",
      id: 17,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [78.549, 508.764, 96.953, 524.247],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.0, 0.0, 0.0, 0.65]",
      content: "3%",
    },
    {
      type: "heading",
      id: 6,
      level: "Doctitle",
      "page number": 1,
      "bounding box": [229.833, 503.024, 248.96, 518.506],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.0, 0.637, 0.622, 0.0]",
      content: "4%",
    },
    {
      type: "heading",
      id: 18,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [78.549, 499.454, 129.319, 509.012],
      "heading level": 2,
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "UNDECIDED",
    },
    {
      type: "paragraph",
      id: 7,
      "page number": 1,
      "bounding box": [229.833, 493.714, 272.142, 503.272],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "DISAGREE",
    },
    {
      type: "paragraph",
      id: 8,
      "page number": 1,
      "bounding box": [151.449, 459.764, 195.452, 495.087],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "1% STRONGLY DISAGREE",
    },
    {
      type: "paragraph",
      id: 19,
      "page number": 1,
      "bounding box": [72, 350.875, 280.148, 438.065],
      font: "Montserrat-Regular",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content:
        "During the COVID-19 pandemic, 70% of respondents agreed that online radicalization and the proliferation of extremist propaganda had increased. Altogether, 76.9% and 92.9% of women agreed with the statement.",
    },
    {
      type: "paragraph",
      id: 20,
      "page number": 1,
      "bounding box": [72, 300.874, 233.498, 328.064],
      font: "Montserrat-Regular",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content: "One interviewee from Indonesia noted that:",
    },
    {
      type: "paragraph",
      id: 3,
      "page number": 1,
      "bounding box": [106.729, 68.231, 279.017, 275.421],
      font: "Montserrat-Italic",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content:
        "“COVID has managed to restrict direct meetings to disseminate propaganda, misinformation and disinformation through most government’s large-scale restrictions to prevent the virus’ spread. However, the tendency to utilize online spaces to disseminate these has increased since the use of online activities is mandatory in various sectors, such as working and education. Most people certainly use online platforms to disseminate false information",
    },
    {
      type: "image",
      id: 49,
      "page number": 1,
      "bounding box": [334.913, 723.401, 335.413, 769.891],
    },
    {
      type: "image",
      id: 48,
      "page number": 1,
      "bounding box": [321.743, 703.734, 338.707, 718.682],
    },
    {
      type: "paragraph",
      id: 21,
      "page number": 1,
      "bounding box": [351, 712.7, 524.418, 769.89],
      font: "Montserrat-Italic",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content:
        "regarding the outbreak, as well as radical ideas targeted at people, including recruiting them as a part of groups.”",
    },
    {
      type: "paragraph",
      id: 30,
      "page number": 1,
      "bounding box": [315.138, 599.739, 496.946, 671.929],
      font: "Montserrat-Bold",
      "font size": 10,
      "text color": "[0.77, 0.25, 0.0, 0.0]",
      content:
        "Figure 8: Respondents’ view to the statement, “Online radicalization and the proliferation of extremist propaganda has increased during COVID-1”.",
    },
    {
      type: "image",
      id: 36,
      "page number": 1,
      "bounding box": [440.012, 529.825, 494.288, 584.553],
    },
    {
      type: "image",
      id: 42,
      "page number": 1,
      "bounding box": [331.628, 544.405, 386.708, 581.26],
    },
    {
      type: "paragraph",
      id: 35,
      "page number": 1,
      "bounding box": [466.574, 542.692, 510.577, 578.014],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "23% STRONGLY AGREE",
    },
    {
      type: "heading",
      id: 40,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [332.088, 558.285, 358.862, 573.767],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.77, 0.25, 0.0, 0.0]",
      content: "47%",
    },
    {
      type: "paragraph",
      id: 41,
      "page number": 1,
      "bounding box": [332.088, 548.975, 360.347, 558.533],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "AGREE",
    },
    {
      type: "image",
      id: 28,
      "page number": 1,
      "bounding box": [348.998, 416.279, 489.448, 556.726],
    },
    {
      type: "image",
      id: 29,
      "page number": 1,
      "bounding box": [348.998, 417.437, 424.083, 556.725],
    },
    {
      type: "image",
      id: 27,
      "page number": 1,
      "bounding box": [399.919, 501.766, 468.235, 539.901],
    },
    {
      type: "image",
      id: 26,
      "page number": 1,
      "bounding box": [365.835, 433.118, 472.604, 539.872],
    },
    {
      type: "image",
      id: 24,
      "page number": 1,
      "bounding box": [383.975, 451.266, 454.472, 521.771],
    },
    {
      type: "image",
      id: 32,
      "page number": 1,
      "bounding box": [402.295, 469.574, 436.157, 503.434],
    },
    {
      type: "image",
      id: 25,
      "page number": 1,
      "bounding box": [442.918, 471.262, 454.478, 492.275],
    },
    {
      type: "image",
      id: 43,
      "page number": 1,
      "bounding box": [383.979, 452.351, 416.001, 491.9],
    },
    {
      type: "image",
      id: 45,
      "page number": 1,
      "bounding box": [416.098, 469.7, 428.096, 479.979],
    },
    {
      type: "image",
      id: 37,
      "page number": 1,
      "bounding box": [450.364, 437.952, 522.361, 478.97],
    },
    {
      type: "image",
      id: 46,
      "page number": 1,
      "bounding box": [390.368, 401.568, 434.282, 473.403],
    },
    {
      type: "image",
      id: 44,
      "page number": 1,
      "bounding box": [320.696, 432.508, 396.757, 468.466],
    },
    {
      type: "heading",
      id: 33,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [477.92, 418.225, 496.641, 433.708],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.0, 0.637, 0.622, 0.0]",
      content: "6%",
    },
    {
      type: "heading",
      id: 38,
      level: "Subtitle",
      "page number": 1,
      "bounding box": [320.897, 412.485, 344.508, 427.967],
      "heading level": 1,
      font: "Montserrat-Bold",
      "font size": 12.701,
      "text color": "[0.0, 0.0, 0.0, 0.65]",
      content: "21%",
    },
    {
      type: "paragraph",
      id: 34,
      "page number": 1,
      "bounding box": [477.92, 408.915, 520.229, 418.473],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "DISAGREE",
    },
    {
      type: "paragraph",
      id: 39,
      "page number": 1,
      "bounding box": [320.897, 403.175, 371.666, 412.733],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "UNDECIDED",
    },
    {
      type: "paragraph",
      id: 31,
      "page number": 1,
      "bounding box": [393.324, 363.03, 437.327, 398.353],
      font: "Montserrat-Bold",
      "font size": 7.841,
      "text color": "[0.0, 0.0, 0.0, 0.85]",
      content: "3% STRONGLY DISAGREE",
    },
    {
      type: "paragraph",
      id: 23,
      "page number": 1,
      "bounding box": [315.138, 312.2, 496.544, 339.39],
      font: "Montserrat-Regular",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content: "Another interviewee from Indonesia observed that:",
    },
    {
      type: "image",
      id: 47,
      "page number": 1,
      "bounding box": [321.743, 70.865, 338.707, 294.982],
    },
    {
      type: "paragraph",
      id: 22,
      "page number": 1,
      "bounding box": [351, 67.595, 524.42, 289.785],
      font: "Montserrat-Italic",
      "font size": 10,
      "text color": "[0.0, 0.0, 0.0, 1.0]",
      content:
        "“(Based on my experience), during 2020-2021 one of the interesting things has been the impact of misinformation and disinformation related to COVID, affecting people’s views and attitudes in responding to, preventing and handling of (the virus). At the beginning of the Indonesian government’s policy on limiting religious activities in places of worship, this issue caused a strong, adverse reaction among extremist groups, giving rise to a narrative that the",
    },
    {
      type: "paragraph",
      id: 1,
      "page number": 1,
      "bounding box": [19.843, 11.829, 562.208, 21.581],
      font: "Montserrat-SemiBold",
      "font size": 8,
      "text color": "[0.0, 0.85, 0.83, 0.0]",
      content:
        "36Gender Analysis of Violent Extremism and the Impact of COVID-19 on Peace and Security in ASEAN",
    },
    {
      type: "image",
      id: 2,
      "page number": 1,
      "bounding box": [-10.866, 13.837, 595.276, 19.842],
    },
  ],
};

export default function ContentPreviewLayout() {
  useEffect(() => {
    const style = document.createElement("style");

    style.innerHTML = pdfLayoutStyles;

    document.head.appendChild(style);

    return () => {
      document.head.removeChild(style);
    };
  }, []);

  let data = pdfJson;
  let pageWidth = 595;
  let pageHeight = 842;
  let scale = 1;
  let onElementClick = (element) => {
    console.log("Clicked element:", element);
  };

  if (!data?.kids) {
    return null;
  }

  const pages = groupByPage(data.kids);

  const pageCount = Number(data["number of pages"]) || 1;

  return (
    <div className="pdf-layout-container">
      {Array.from({ length: pageCount }, (_, index) => {
        const pageNumber = index + 1;

        const elements = pages.get(pageNumber) ?? [];

        /*
         * Sort by z-index where available.
         * Otherwise preserve the source order.
         */
        const sortedElements = [...elements].sort(compareElements);

        const pageMetadata = data.pages?.find(
          (page) => page.page === pageNumber,
        );

        const currentPageWidth = pageMetadata?.width ?? pageWidth;

        const currentPageHeight = pageMetadata?.height ?? pageHeight;

        return (
          <div
            key={pageNumber}
            className="pdf-layout-page"
            style={{
              width: currentPageWidth * scale,

              height: currentPageHeight * scale,
            }}
            data-page={pageNumber}
          >
            {sortedElements.map((element) => (
              <PdfElement
                key={`${pageNumber}-${element.id}`}
                element={element}
                pageHeight={currentPageHeight}
                scale={scale}
                onClick={onElementClick}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
